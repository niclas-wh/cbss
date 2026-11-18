# -*- coding: utf-8 -*-
"""Segmentierter Traeger -- Rhino 8 / Grasshopper 1 / Python 3, Script-Modus.

EINRICHTUNG
  Den gesamten Code in eine Python-3-Script-Komponente einfuegen, nicht als
  SDK-/RunScript-Klasse.
    G          Curve Type Hint, LIST ACCESS; gerichtete offene gerade Linien.
               Rhino-Line oder geometrisch lineare Rhino-Curve je Eintrag.
    QS_Start   str Type Hint, LIST ACCESS; XYZ-JSON-Liste aus section_block.
    QS_Ende    str Type Hint, LIST ACCESS; XYZ-JSON-Liste aus section_profile_block.
    Segmente   str Type Hint, ITEM ACCESS, OPTIONAL (Required deaktivieren);
               Standard 0, derselbe Abstand fuer alle Kurven.
  G, QS_Start und QS_Ende muessen gleich lang sein, Zuordnung strikt nach Index.
  Keine Wiederholung/Verkuerzung; None-Eintraege nicht entfernen.
  Die Komponentenports manuell anpassen: Segment in Segmente umbenennen,
  einen alten Segment_Laenge-Port entfernen; G und beide QS auf List einstellen.
  Ausgaenge neben dem optionalen Standardausgang out unveraendert:
    Loft_Oben, Loft_Seiten, Loft_Unten, Brep_Anfang, Brep_Ende, Brep_Zwischen, Gesamt.

DATENVERTRAG
  Nur {"xyz_points": [[x,y,z], ...]} mit genau sieben Weltpunkten 0 bis 6.
  Lokale Punktformate, gemischte oder wiederholte Schluessel sind ungueltig.
  Punkt 0 liegt am jeweiligen gerichteten G-Endpunkt, danach folgen rechts
  Oberkante, Knick und Unterkante, links Unterkante, Knick und Oberkante.
  Symmetrisches Profil, positive Breiten/Tiefen, Randfolge im Uhrzeigersinn
  relativ zur Gradientenrichtung. Punkt 0 NICHT als Schlusspunkt wiederholen.
  Beide Profile muessen planar und korrespondierend sein; jede aus zwei
  Profilkanten gebildete Vierpunkt-Mantelflaeche muss ebenfalls planar sein.
  Eingabepunkte werden weder verschoben/projiziert noch umnummeriert.

SEGMENTIERUNG UND EINHEITEN
  Alle Koordinaten und Abstaende in Rhino-Modelleinheiten; keine Umrechnung.
  Segmente: Panel mit genau einer Zahl ohne Einheit (z.B. 2.5 oder 2,5).
  None/ohne Anschluss, 0 oder Abstand >= G-Laenge: keine Zwischenstationen.
  Negative/nicht endliche und positive Abstaende <= Dokumenttoleranz ablehnen.
  Maximal 10000 Segmente. Jede innere Schnittebene steht normal auf G.
  Jede Verbindungskante wird einzeln mit dieser Ebene geschnitten, NICHT
  mit einem gemeinsamen Stationsfaktor interpoliert. Schnittparameter muessen
  eindeutig, streng innen und entlang jeder Verbindung streng monoton sein.
  Unmoegliche, degenerierte oder falsch geordnete Schnitte liefern eine
  Stations-/Kantenmeldung, keine geklemmten oder verschobenen Ersatzpunkte.

AUSGABEN
  Datenbaum je Ausgang mit einem Zweig {i} pro G[i]. Jeder Zweig enthaelt
  die Einzelflaechen der zugehoerigen Kurve oder None, falls keine entstehen.
  Einzelfehler melden G[i] und setzen nur dessen sieben Zweige auf None;
  nachfolgende Kurven behalten ihre Indizes. Bei ungleichen Listenlaengen
  keine Berechnung: alle Zweige je G-Index None und Fehlermeldung.
  Leeres G liefert leere Datenbaeume und eine Fehlermeldung.
  Loft_Oben: 0-1, 6-0; Loft_Seiten: 1-2, 2-3, 4-5, 5-6; Loft_Unten: 3-4.
  Reihenfolge je Loft-Ausgang: Segment, Profilkante.
  Brep_Anfang/Brep_Ende: nach aussen orientierte Abschluesse.
  Brep_Zwischen: genau eine Abschlussflaeche je innerer Grenze, als Ende des
  vorherigen Segments orientiert. Ohne innere Grenzen None.
  Intern wird jedes Segment auf Gueltigkeit, Geschlossenheit und Orientierung
  geprueft. Gesamt enthaelt dessen nach aussen orientierte Einzelflaechen
  einschliesslich BEIDER Segmentabschluesse, keine Volumen-Breps.
  Jedes Skript ist eigenstaendig; keine Importe aus anderen Projektdateien.
"""

import json
import math


def _number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(label + ": endliche Zahl erwartet.")
    try:
        value = float(value)
    except OverflowError:
        raise ValueError(label + ": Zahl ist zu gross.")
    if not math.isfinite(value):
        raise ValueError(label + ": endliche Zahl erwartet.")
    return value


def _panel_number(value, label):
    """Panel-Text oder numerischen Wert lesen; JSON-Zahlen bleiben strikt."""
    if isinstance(value, str):
        text = value.strip()
        if not text or len(text.splitlines()) != 1:
            raise ValueError(label + ": genau einen Zahlenwert im Panel eingeben.")
        try:
            value = float(text.replace(",", "."))
        except ValueError:
            raise ValueError(label + ": Zahl ohne Einheit erwartet, z.B. 2.5 oder 2,5.")
    return _number(value, label)


def _distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _point_segment_distance(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    q = dx * dx + dy * dy
    if q == 0:
        return _distance(p, a)
    u = max(0.0, min(1.0, ((p[0]-a[0])*dx + (p[1]-a[1])*dy) / q))
    return _distance(p, (a[0] + u*dx, a[1] + u*dy))


def _cross(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])


def _edges_touch(a, b, c, d, tol):
    # Echte Kreuzung oder Abstand kleiner Dokumenttoleranz.
    ab_c, ab_d = _cross(a,b,c), _cross(a,b,d)
    cd_a, cd_b = _cross(c,d,a), _cross(c,d,b)
    if ((ab_c > 0) != (ab_d > 0) and
            (cd_a > 0) != (cd_b > 0) and
            ab_c != 0 and ab_d != 0 and cd_a != 0 and cd_b != 0):
        return True
    return min(_point_segment_distance(a,c,d), _point_segment_distance(b,c,d),
               _point_segment_distance(c,a,b), _point_segment_distance(d,a,b)) <= tol


def _validate_polygon(points, tol, label):
    n = len(points)
    if n < 3:
        raise ValueError(label + ": mindestens drei Randpunkte erforderlich.")
    for i in range(n):
        for j in range(i+1, n):
            if _distance(points[i], points[j]) <= tol:
                raise ValueError(label + ": doppelte/zu nahe Punkte {} und {}. "
                                 "Den ersten Punkt nicht als Schlusspunkt wiederholen."
                                 .format(i, j))
    perimeter = sum(_distance(points[i], points[(i+1) % n]) for i in range(n))
    area2 = sum(_cross((0,0), points[i], points[(i+1) % n]) for i in range(n))
    if abs(area2) <= tol * perimeter:
        raise ValueError(label + ": Profil ist flaechenlos oder zu klein.")
    for i in range(n):
        # Ueberlappende angrenzende Kanten (Ruecklauf) ebenfalls ablehnen.
        a, b, c = points[i-1], points[i], points[(i+1) % n]
        if (_point_segment_distance(c, a, b) <= tol or
                _point_segment_distance(a, b, c) <= tol):
            raise ValueError(label + ": ueberlappende Kanten bei Punkt {}.".format(i))
        for j in range(i+1, n):
            if j == i+1 or (i == 0 and j == n-1):
                continue
            if _edges_touch(points[i], points[(i+1) % n],
                            points[j], points[(j+1) % n], tol):
                raise ValueError(label + ": Selbstschnitt/Beruehrung zwischen "
                                 "Kanten {} und {}.".format(i, j))
    return area2


class _ObjectPairs(list):
    """Objekte von Arrays unterscheiden und doppelte JSON-Schluessel erkennen."""


def _read_profile(value, label):
    if isinstance(value, str):
        try:
            value = json.loads(value, object_pairs_hook=_ObjectPairs)
        except (ValueError, TypeError) as exc:
            raise ValueError(label + ": ungueltiges JSON: " + str(exc))
    if isinstance(value, dict):
        blocks = list(value.items())
    elif isinstance(value, _ObjectPairs):
        blocks = value
    else:
        raise ValueError(label + ': JSON-Objekt mit ausschliesslich "xyz_points" erwartet.')
    if len(blocks) != 1 or blocks[0][0] != "xyz_points":
        raise ValueError(label + ': genau ein Schluessel "xyz_points" erforderlich; '
                         'lokale, gemischte und wiederholte Punktformate sind ungueltig.')
    raw = blocks[0][1]
    if isinstance(raw, _ObjectPairs) or not isinstance(raw, (list, tuple)) or len(raw) != 7:
        raise ValueError(label + ': "xyz_points" muss genau sieben Randpunkte enthalten.')
    points = []
    for i, point in enumerate(raw):
        where = "{}: Punkt {}".format(label, i)
        if (isinstance(point, _ObjectPairs) or not isinstance(point, (list, tuple))
                or len(point) != 3):
            raise ValueError(where + ": [x,y,z] erwartet.")
        points.append(tuple(_number(c, where) for c in point))
    return points


def _sub3(a, b):
    return tuple(x-y for x, y in zip(a, b))


def _dot3(a, b):
    return sum(x*y for x, y in zip(a, b))


def _cross3(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def _norm3(a):
    return math.hypot(*a)


def _coords(point):
    return (point.X, point.Y, point.Z)


def _profile_plane(points, tol, label):
    """Stabile Ebene ermitteln, ohne die gelieferten Punkte zu veraendern."""
    delta = [_sub3(p, points[0]) for p in points]
    longest = max(delta, key=_norm3)
    span = _norm3(longest)
    if not math.isfinite(span) or span <= tol:
        raise ValueError(label + ": Profil/Flaeche ist degeneriert oder zu klein.")
    x = tuple(c/span for c in longest)
    normal = max((_cross3(x, d) for d in delta), key=_norm3)
    height = _norm3(normal)
    if not math.isfinite(height) or height <= tol:
        raise ValueError(label + ": Profil/Flaeche ist flaechenlos oder zu klein.")
    normal = tuple(c/height for c in normal)
    if any(abs(_dot3(d, normal)) > tol for d in delta):
        raise ValueError(label + ": Punkte sind nicht koplanar (Dokumenttoleranz).")
    return normal


def _validate_profile(points, anchor, tangent, tol, label, symmetric=False):
    if _norm3(_sub3(points[0], anchor)) > tol:
        raise ValueError(label + ": Punkt 0 muss am zugehoerigen Gradientenpunkt liegen.")
    normal = _profile_plane(points, tol, label)
    alignment = _dot3(normal, tangent)
    if abs(alignment) <= 1e-12:
        raise ValueError(label + ": Profilebene liegt laengs statt quer zur Gradiente.")
    if alignment < 0:
        normal = tuple(-c for c in normal)
    width = _sub3(points[1], points[0])
    span = _norm3(width)
    if span <= tol:
        raise ValueError(label + ": Oberkante 0-1 ist zu kurz.")
    x = tuple(c/span for c in width)
    y = _cross3(normal, x)
    delta = [_sub3(p, points[0]) for p in points]
    local = [(_dot3(d, x), _dot3(d, y)) for d in delta]
    if _validate_polygon(local, tol, label) >= 0:
        raise ValueError(label + ": ungueltige Punktreihenfolge; keine Umnummerierung erlaubt.")
    # Schnitte geneigter Endprofile muessen nicht erneut symmetrisch sein.
    if symmetric:
        # Gleiche Querrichtung wie section, ohne XYZ-Punkte neu zu platzieren.
        up = (0.0, 0.0, 1.0)
        projected = tuple(up[i] - _dot3(up, tangent)*tangent[i] for i in range(3))
        if _norm3(projected) <= 1e-8:
            up = (0.0, 1.0, 0.0)
            projected = tuple(up[i] - _dot3(up, tangent)*tangent[i] for i in range(3))
        right_axis = _cross3(projected, tangent)
        right_length = _norm3(right_axis)
        right_axis = tuple(c/right_length for c in right_axis)
        perpendicular_match = _norm3(tuple(width[i] - span*right_axis[i]
                                          for i in range(3))) <= tol
        # Lotrecht bleibt Welt-Z Kreuz t, auch nahe der vertikalen Ersatzlage.
        horizontal_right = _cross3((0.0, 0.0, 1.0), tangent)
        horizontal_length = _norm3(horizontal_right)
        vertical_match = (horizontal_length > 1e-12 and
                          _norm3(tuple(width[i] - span*horizontal_right[i]/horizontal_length
                                       for i in range(3))) <= tol)
        if not perpendicular_match and not vertical_match:
            raise ValueError(label + ": Oberkante 0-1 entspricht nicht der section-Querrichtung.")
        for right, left in ((1, 6), (2, 5), (3, 4)):
            a, b = local[right], local[left]
            if (a[0] <= tol or b[0] >= -tol or abs(a[0]+b[0]) > tol
                    or abs(a[1]-b[1]) > tol):
                raise ValueError(label + ": falsche Punktzuordnung/Symmetrie bei {} und {}."
                                 .format(right, left))
        if abs(local[1][1]) > tol or abs(local[6][1]) > tol:
            raise ValueError(label + ": Punkte 6, 0 und 1 muessen die Oberkante bilden.")
        if local[2][1] >= -tol or local[3][1] >= -tol:
            raise ValueError(label + ": Hoehe_1 und Hoehe_2 muessen positiv sein.")


def _validate_mantle(start, end, tol, label):
    for j in range(7):
        k = (j+1) % 7
        quad = [start[j], start[k], end[k], end[j]]
        normal = _profile_plane(quad, tol, label + ": Mantelkante {}-{}".format(j, k))
        direction = _sub3(quad[1], quad[0])
        span = _norm3(direction)
        if span <= tol:
            raise ValueError(label + ": Mantelkante {} ist zu kurz.".format(j))
        x = tuple(c/span for c in direction)
        y = _cross3(normal, x)
        local = [(_dot3(_sub3(p, quad[0]), x), _dot3(_sub3(p, quad[0]), y))
                 for p in quad]
        _validate_polygon(local, tol, label + ": Mantelkante {}-{}".format(j, k))


def _stations(length, step, tol):
    if not math.isfinite(step) or step < 0:
        raise ValueError("Segmente muss endlich und >= 0 sein.")
    if step > 0 and step <= tol:
        raise ValueError("Segmente ist kleiner/gleich der Dokumenttoleranz.")
    if step == 0 or step >= length:
        return [0.0, length]
    ratio = length / step
    if not math.isfinite(ratio) or ratio > 10000:
        raise ValueError("Mehr als 10000 Segmente: Segmentabstand vergroessern.")
    count = int(math.ceil(ratio))
    result = [0.0]
    for k in range(1, count):
        s = k * step
        if length - s > tol:
            result.append(s)
    result.append(length)
    return result


def _gradient(g, rg, tol):
    if isinstance(g, rg.Line):
        if not g.IsValid:
            raise ValueError("G: ungueltige Linie.")
        first, last = g.From, g.To
    elif isinstance(g, rg.Curve):
        if not g.IsValid or g.IsClosed or not g.IsLinear(tol):
            raise ValueError("G: genau eine offene gerade Linie erforderlich; keine echte Kurve.")
        first, last = g.PointAtStart, g.PointAtEnd
        # Auch ruecklaufende, kollineare Kurven sind keine gerichtete Linie.
        chord = first.DistanceTo(last)
        curve_length = g.GetLength()
        if not math.isfinite(curve_length) or abs(curve_length - chord) > tol:
            raise ValueError("G: ruecklaufende oder mehrfach durchlaufene Linie ungueltig.")
    else:
        raise ValueError("G: Rhino-Line oder lineare Rhino-Curve erforderlich; "
                         "Type Hint Curve und Item Access verwenden (keine Liste).")
    line = rg.Line(first, last)
    if not line.IsValid or not math.isfinite(line.Length) or line.Length <= tol:
        raise ValueError("G: Linie ist ungueltig oder zu kurz.")
    tangent = line.Direction
    if not tangent.Unitize():
        raise ValueError("G: keine eindeutige Richtung.")
    return line, tangent


def _cut_profile(start, end, plane, previous, tol, label, rg):
    points, parameters = [], []
    for j, (a, b) in enumerate(zip(start, end)):
        where = label + ": Verbindungskante {}".format(j)
        edge = rg.Line(rg.Point3d(*a), rg.Point3d(*b))
        denominator = rg.Vector3d.Multiply(edge.Direction, plane.Normal)
        if abs(denominator) <= tol:
            detail = ("Schnitt nicht eindeutig (Kante in Schnittebene)."
                      if abs(plane.DistanceTo(edge.From)) <= tol
                      else "kein eindeutiger Schnitt (Kante parallel zur Schnittebene).")
            raise ValueError(where + ": " + detail)
        ok, parameter = rg.Intersect.Intersection.LinePlane(edge, plane)
        if not ok or not math.isfinite(parameter):
            raise ValueError(where + ": kein eindeutiger Ebenenschnitt.")
        if not 0.0 < parameter < 1.0:
            raise ValueError(where + ": Schnitt liegt nicht strikt innerhalb der endlichen Kante.")
        if (parameter * edge.Length <= tol or (1.0-parameter) * edge.Length <= tol
                or (parameter-previous[j]) * edge.Length <= tol):
            raise ValueError(where + ": Schnittparameter nicht streng monoton/zu nahe an Grenze.")
        point = edge.PointAt(parameter)
        if not point.IsValid or abs(plane.DistanceTo(point)) > tol:
            raise ValueError(where + ": ungueltiger Schnittpunkt ausserhalb der Schnittebene.")
        points.append(_coords(point))
        parameters.append(parameter)
    return points, parameters


def _face_normal(face):
    normal = face.NormalAt(face.Domain(0).Mid, face.Domain(1).Mid)
    if face.OrientationIsReversed:
        normal.Reverse()
    return normal


def _single_faces(brep, label):
    result = []
    for face in brep.Faces:
        copy = face.DuplicateFace(False)
        if copy is None or not copy.IsValid or copy.Faces.Count != 1:
            raise ValueError(label + ": Duplizieren der Einzelflaeche fehlgeschlagen.")
        result.append(copy)
    return result


def _build(g, start, end, segments):
    import Rhino
    import Rhino.Geometry as rg

    doc = Rhino.RhinoDoc.ActiveDoc
    if doc is None:
        raise ValueError("Kein aktives Rhino-Dokument fuer Toleranz.")
    tol = doc.ModelAbsoluteTolerance
    if not math.isfinite(tol) or tol <= 0:
        raise ValueError("Rhino-Dokumenttoleranz muss positiv und endlich sein.")
    step = _panel_number(0 if segments is None else segments, "Segmente")
    line, tangent = _gradient(g, rg, tol)
    stations = _stations(line.Length, step, tol)
    direction = _coords(tangent)
    world0 = _read_profile(start, "QS_Start")
    world1 = _read_profile(end, "QS_Ende")
    _validate_profile(world0, _coords(line.From), direction, tol, "QS_Start", True)
    _validate_profile(world1, _coords(line.To), direction, tol, "QS_Ende", True)
    _validate_mantle(world0, world1, tol, "Start-/Endprofile")

    caps, vertices = [], []
    previous = [0.0] * 7
    for index, station in enumerate(stations):
        label = "Station {} (s={:.12g} Modelleinheiten)".format(index, station)
        if index == 0:
            world, anchor = world0, line.From
        elif index == len(stations)-1:
            world, anchor = world1, line.To
            for j in range(7):
                if (1.0-previous[j]) * _norm3(_sub3(world1[j], world0[j])) <= tol:
                    raise ValueError(label + ": Verbindungskante {}: Endparameter nicht monoton."
                                     .format(j))
        else:
            anchor = line.From + tangent * station
            plane = rg.Plane(anchor, tangent)
            world, previous = _cut_profile(world0, world1, plane, previous, tol, label, rg)
        _validate_profile(world, _coords(anchor), direction, tol, label)
        pts = [rg.Point3d(*p) for p in world]
        profile = rg.PolylineCurve(pts + [pts[0]])
        planar = rg.Brep.CreatePlanarBreps(profile, tol)
        if (not planar or len(planar) != 1 or not planar[0].IsValid
                or planar[0].Faces.Count != 1):
            raise ValueError(label + ": genau eine gueltige ebene Abschlussflaeche erforderlich.")
        cap = planar[0]
        alignment = rg.Vector3d.Multiply(_face_normal(cap.Faces[0]), tangent)
        if not math.isfinite(alignment) or abs(alignment) <= 1e-12:
            raise ValueError(label + ": Abschlussorientierung nicht bestimmbar.")
        if alignment < 0:
            cap.Flip()
        caps.append(cap)
        vertices.append(pts)

    top_faces, side_faces, bottom_faces = [], [], []
    intermediate_faces, all_faces = [], []
    for i in range(len(stations)-1):
        label = "Segment {} (s={:.12g} bis {:.12g})".format(i, stations[i], stations[i+1])
        _validate_mantle([_coords(p) for p in vertices[i]],
                         [_coords(p) for p in vertices[i+1]], tol, label)
        sides, targets = [], []
        for j in range(7):
            k = (j+1) % 7
            a = rg.LineCurve(vertices[i][j], vertices[i][k])
            b = rg.LineCurve(vertices[i+1][j], vertices[i+1][k])
            loft = rg.Brep.CreateFromLoft([a, b], rg.Point3d.Unset,
                                         rg.Point3d.Unset, rg.LoftType.Straight, False)
            if (not loft or len(loft) != 1 or not loft[0].IsValid
                    or loft[0].Faces.Count != 1 or not loft[0].Faces[0].IsPlanar(tol)):
                raise ValueError(label + ": ebener Loft an Kante {}-{} fehlgeschlagen."
                                 .format(j, k))
            side = loft[0]
            outward = rg.Vector3d.CrossProduct(vertices[i+1][j] - vertices[i][j],
                                                vertices[i][k] - vertices[i][j])
            if not outward.Unitize():
                raise ValueError(label + ": Orientierung an Kante {} unbestimmt.".format(j))
            alignment = rg.Vector3d.Multiply(_face_normal(side.Faces[0]), outward)
            if not math.isfinite(alignment) or abs(alignment) <= 1e-12:
                raise ValueError(label + ": Loftorientierung an Kante {} unbestimmt.".format(j))
            if alignment < 0:
                side.Flip()
            sides.append(side)
            targets.append(top_faces if j in (0, 6) else bottom_faces if j == 3 else side_faces)
        start_cap = caps[i].DuplicateBrep()
        start_cap.Flip()
        end_cap = caps[i+1].DuplicateBrep()
        joined = rg.Brep.JoinBreps(sides + [start_cap, end_cap], tol)
        if (not joined or len(joined) != 1 or not joined[0].IsValid
                or not joined[0].IsSolid):
            raise ValueError(label + ": kein gueltiger geschlossener Volumenkoerper; "
                             "Profile und Segmentabstand pruefen.")
        solid = joined[0]
        if solid.SolidOrientation == rg.BrepSolidOrientation.Inward:
            solid.Flip()
        if not solid.IsValid or solid.SolidOrientation != rg.BrepSolidOrientation.Outward:
            raise ValueError(label + ": gueltige Aussenorientierung nicht bestimmbar.")
        all_faces.extend(_single_faces(solid, label))
        for side, target in zip(sides, targets):
            target.extend(_single_faces(side, label))

    for i in range(1, len(stations)-1):
        intermediate_faces.extend(_single_faces(caps[i], "Zwischenabschluss {}".format(i)))
    first = caps[0].DuplicateBrep()
    first.Flip()
    result = (top_faces, side_faces, bottom_faces,
              _single_faces(first, "Brep_Anfang"), _single_faces(caps[-1], "Brep_Ende"),
              intermediate_faces, all_faces)
    return tuple(faces if faces else None for faces in result)


def _as_list(value):
    import Rhino.Geometry as rg
    if value is None:
        return []
    if isinstance(value, (rg.Curve, rg.Line, str, dict)):
        return [value]
    try:
        return list(value)
    except TypeError:
        return [value]


def _run_component():
    from Grasshopper import DataTree
    from Grasshopper.Kernel import GH_RuntimeMessageLevel
    from Grasshopper.Kernel.Data import GH_Path

    def report(message):
        ghenv.Component.AddRuntimeMessage(GH_RuntimeMessageLevel.Error, message)

    curves = _as_list(globals().get("G"))
    starts = _as_list(globals().get("QS_Start"))
    ends = _as_list(globals().get("QS_Ende"))
    outputs = tuple(DataTree[object]() for _ in range(7))
    if not curves:
        report("G: mindestens eine gerichtete gerade Linie erforderlich.")
    valid_lengths = len(starts) == len(ends) == len(curves)
    if not valid_lengths:
        report("Listenlaengen: G={}, QS_Start={}, QS_Ende={}; genau ein Start-/End-QS je G erforderlich."
               .format(len(curves), len(starts), len(ends)))
    for index, curve in enumerate(curves):
        result = (None,) * 7
        if valid_lengths:
            try:
                if starts[index] is None or ends[index] is None:
                    raise ValueError("QS_Start oder QS_Ende fehlt an diesem Index.")
                result = _build(curve, starts[index], ends[index], globals().get("Segmente"))
            except Exception as exc:
                report("G[{}]: {}".format(index, exc))
        path = GH_Path(index)
        for tree, faces in zip(outputs, result):
            for face in faces if faces else [None]:
                tree.Add(face, path)
    return outputs


if "ghenv" in globals():
    (Loft_Oben, Loft_Seiten, Loft_Unten, Brep_Anfang, Brep_Ende,
     Brep_Zwischen, Gesamt) = _run_component()

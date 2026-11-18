# -*- coding: utf-8 -*-
"""Endprofil mit ebenen Mantelflaechen -- Rhino 8 / GH 1 / Python 3 Script-Modus.

Eingaenge:
  G: Curve Type Hint, LIST ACCESS; gerichtete gerade Linien.
  QS_Start: str Type Hint, LIST ACCESS; XYZ-JSON-Liste aus section.
  Beide Listen muessen gleich lang sein; Zuordnung strikt nach Index.
  Keine Wiederholung/Verkuerzung, None-Platzhalter nicht entfernen.
  Alle weiteren Eingaenge Item Access, gemeinsam fuer alle Kurven:
  Fahrbahnbreite: str Type Hint; Gesamtbreite am Ende.
  Wahl_Abmessung_1, Wahl_Abmessung_2: str Type Hint; jeweils Breite_1,
    Hoehe_1, Breite_2 oder Hoehe_2 (zwei verschiedene Namen).
  Abmessung_1, Abmessung_2: str Type Hint; zugehoerige positive Zahlen.
  Ende_Rechtwinklig: str Type Hint, OPTIONAL, Standard true.
  Unten_Eben: str Type Hint, OPTIONAL, Standard false.
  Bei Unten_Eben=true auch Wahl_Abmessung_2 und Abmessung_2 OPTIONAL markieren:
    sie werden ignoriert; Wahl_Abmessung_1 darf dann nicht Hoehe_2 sein.
  Optionale Ports: Required deaktivieren. Kein Start_Rechtwinklig-Eingang.
Ausgaenge neben out: Abmessungen, G, QS_Start, QS_Ende.
Alle Masse in Rhino-Modelleinheiten. Abmessungen: Datenbaum mit Textzeilen
je Kurve im Zweig {i}, auf 3 Nachkommastellen; JSON behaelt volle Genauigkeit.
G, QS_Start und QS_Ende sind indexgleiche Listen. G und gueltig zugeordnete
QS_Start-Eintraege werden unveraendert durchgereicht. Bei Einzelfehlern:
QS_Ende[i]=None und Abmessungen-Zweig {i} mit Fehlertext inklusive G-Index;
andere Kurven bleiben erhalten. Die GH-Laufzeitmeldung bleibt zusaetzlich bestehen.
Bei Laengenfehlern keine Berechnung: QS_Start/QS_Ende je G-Index None,
Abmessungen je G-Zweig mit Fehlertext. Leeres G: leere Ausgaben und Fehlermeldung.

Sieben symmetrische Punkte 0..6 wie bei section; nur xyz_points-JSON.
Unten_Eben legt Welt-Z der Punkte 3/4 am Ende auf die Startwerte fest.
Nicht eindeutige oder unmoegliche Vorgaben werden abgelehnt, nicht angenaehert.
Insbesondere kann Breite_1 + Hoehe_1 die unteren Masse nicht eindeutig bestimmen.
Jedes Skript ist eigenstaendig in die GH-Script-Komponente kopierbar.
"""

import json
import math

_NAMES = ("Breite_1", "Hoehe_1", "Breite_2", "Hoehe_2")


def _number(value, label):
    if isinstance(value, str):
        text = value.strip()
        if not text or len(text.splitlines()) != 1:
            raise ValueError(label + ": genau einen Zahlenwert eingeben.")
        try:
            value = float(text.replace(",", "."))
        except ValueError:
            raise ValueError(label + ": Zahl ohne Einheit erwartet.")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(label + ": endliche Zahl erforderlich.")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(label + ": endliche Zahl erforderlich.")
    return value


def _boolean(value, label, default):
    if value is None or (isinstance(value, str) and not value.strip()):
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in ("true", "false"):
        return value.strip().lower() == "true"
    raise ValueError(label + ": true oder false erwartet.")


def _basis(curve, perpendicular):
    import Rhino.Geometry as rg
    t = curve.PointAtEnd - curve.PointAtStart
    t.Unitize()
    up = rg.Vector3d.ZAxis
    if perpendicular:
        y = up - t * rg.Vector3d.Multiply(up, t)
        if y.Length <= 1e-8:
            up = rg.Vector3d.YAxis
            y = up - t * rg.Vector3d.Multiply(up, t)
        y.Unitize()
        x = rg.Vector3d.CrossProduct(y, t)
    else:
        x = rg.Vector3d.CrossProduct(up, t)
        if x.Length <= 1e-12:
            raise ValueError("Lotrechtes Profil bei vertikaler Gradiente nicht definierbar.")
        y = up
    x.Unitize()
    return x, y, t


def _read_start(value, curve, tol):
    import Rhino.Geometry as rg
    data = json.loads(value) if isinstance(value, str) else value
    if not isinstance(data, dict) or set(data) != {"xyz_points"}:
        raise ValueError('QS_Start: ausschliesslich {"xyz_points": [...]} erwartet.')
    raw = data["xyz_points"]
    if not isinstance(raw, (list, tuple)) or len(raw) != 7:
        raise ValueError("QS_Start: sieben Randpunkte 0..6 erforderlich.")
    points = []
    for row in raw:
        if not isinstance(row, (list, tuple)) or len(row) != 3:
            raise ValueError("QS_Start: jeder Punkt muss [x,y,z] enthalten.")
        if any(isinstance(c, str) for c in row):
            raise ValueError("QS_Start: numerische XYZ-Koordinaten erforderlich.")
        points.append(rg.Point3d(*[_number(c, "QS_Start") for c in row]))
    if points[0].DistanceTo(curve.PointAtStart) > tol:
        raise ValueError("QS_Start: Punkt 0 muss am Anfang von G liegen.")
    x, _, t = _basis(curve, True)
    y = (points[0] - (points[3] + (points[4]-points[3])*0.5))
    if y.Length <= tol:
        raise ValueError("QS_Start: ungueltige Hoehenachse.")
    y.Unitize()
    if abs(rg.Vector3d.Multiply(x, y)) > 1e-10:
        raise ValueError("QS_Start: keine symmetrische Querebene.")
    normal = rg.Vector3d.CrossProduct(x, y)
    if rg.Vector3d.Multiply(normal, t) <= 1e-12:
        raise ValueError("QS_Start: ungueltige Profilorientierung.")
    coords = []
    for p in points:
        d = p-points[0]
        if abs(rg.Vector3d.Multiply(d, normal)) > tol:
            raise ValueError("QS_Start: Punkte sind nicht koplanar.")
        coords.append((rg.Vector3d.Multiply(d,x), rg.Vector3d.Multiply(d,y)))
    f, b1, b2 = 2*coords[1][0], 2*coords[2][0], 2*coords[3][0]
    h1, h2 = -coords[2][1], -coords[3][1]
    if min(f,b1,b2,h1,h2) <= tol:
        raise ValueError("QS_Start: positive Breiten und Tiefen erforderlich.")
    expected = ((0,0),(f/2,0),(b1/2,-h1),(b2/2,-h2),
                (-b2/2,-h2),(-b1/2,-h1),(-f/2,0))
    if any(math.hypot(a-c,b-d) > tol for (a,b),(c,d) in zip(coords,expected)):
        raise ValueError("QS_Start: symmetrisches Profil mit Punktfolge 0..6 erforderlich.")
    _validate_profile(points, tol, "QS_Start")
    return points


def _validate_profile(points, tol, label):
    import Rhino.Geometry as rg
    for i, p in enumerate(points):
        if any(p.DistanceTo(q) <= tol for q in points[i+1:]):
            raise ValueError(label + ": doppelte oder zu nahe Punkte.")
    outline = rg.PolylineCurve(points + [points[0]])
    if rg.Intersect.Intersection.CurveSelf(outline, tol).Count:
        raise ValueError(label + ": Selbstschnitt oder ueberlappende Kanten.")
    caps = rg.Brep.CreatePlanarBreps(outline, tol)
    if not caps or len(caps) != 1 or not caps[0].IsValid:
        raise ValueError(label + ": kein gueltiger ebener Querschnitt.")


# Polynome: Monome sind sortierte Tupel der unbekannten Massindizes.
def _add(a, b, factor=1.0):
    result = dict(a)
    for key, value in b.items():
        result[key] = result.get(key, 0.0) + factor*value
    return result


def _mul(a, b):
    result = {}
    for ka, va in a.items():
        for kb, vb in b.items():
            key = tuple(sorted(ka+kb))
            result[key] = result.get(key, 0.0) + va*vb
    return result


def _substitute(poly, variable, replacement):
    result = {}
    for key, value in poly.items():
        term = {(): value}
        for index in key:
            term = _mul(term, replacement if index == variable else {(index,): 1.0})
        result = _add(result, term)
    return result


def _clean(poly):
    scale = max((abs(v) for v in poly.values()), default=0.0)
    if scale <= 1e-12:
        return {}
    return {k:v/scale for k,v in poly.items() if abs(v) > max(1e-12, scale*1e-12)}


def _solve(equations, unknown):
    remaining = set(unknown)
    substitutions = []
    while remaining:
        equations = [_clean(eq) for eq in equations]
        if any(eq and all(not key for key in eq) for eq in equations):
            raise ValueError("Massvorgaben widersprechen den Ebenheitsbedingungen.")
        linear = [eq for eq in equations if any(eq) and all(len(k) <= 1 for k in eq)]
        if not linear:
            if len(remaining) != 1:
                raise ValueError("Masskombination besitzt keine eindeutige Loesung.")
            variable = next(iter(remaining))
            polynomial = next((e for e in equations if (variable,variable) in e), None)
            if polynomial is None:
                raise ValueError("Masskombination besitzt keine eindeutige Loesung.")
            a = polynomial.get((variable,variable),0.0)
            b = polynomial.get((variable,),0.0)
            c = polynomial.get((),0.0)
            discriminant = b*b-4*a*c
            if discriminant < -1e-12:
                raise ValueError("Massvorgaben besitzen keine reelle Loesung.")
            root = math.sqrt(max(0.0,discriminant))
            q = -0.5*(b+math.copysign(root,b))
            roots = [q/a, c/q] if q else [-b/(2*a)]
            candidates = []
            for value in roots:
                values = {variable:value}
                for index,replacement in reversed(substitutions):
                    values[index] = sum(v*math.prod(values[i] for i in key)
                                        for key,v in replacement.items())
                if not any(all(abs(values[i]-other[i]) <= 1e-12 for i in values)
                           for other in candidates):
                    candidates.append(values)
            return candidates
        eq = max(linear, key=lambda e: max(abs(v) for k,v in e.items() if k))
        key = max((k for k in eq if k), key=lambda k: abs(eq[k]))
        variable = key[0]
        pivot = eq[key]
        replacement = {k:-v/pivot for k,v in eq.items() if k != key}
        substitutions.append((variable,replacement))
        equations = [_substitute(other,variable,replacement) for other in equations if other is not eq]
        remaining.remove(variable)
    # Konstante Restfehler werden geometrisch mit Dokumenttoleranz geprueft.
    values = {}
    for variable, replacement in reversed(substitutions):
        values[variable] = sum(v * math.prod(values[i] for i in key)
                               for key,v in replacement.items())
    return [values]


def _end_geometry(start, origin, x, y, f, values, bottom, tol):
    import Rhino.Geometry as rg
    if any(not math.isfinite(v) or v <= tol for v in values.values()):
        raise ValueError("Berechnete Masse sind nicht positiv/endlich oder zu klein.")
    b1,h1,b2,h2 = (values[i] for i in range(4))
    local = ((0,0),(f/2,0),(b1/2,-h1),(b2/2,-h2),(-b2/2,-h2),(-b1/2,-h1),(-f/2,0))
    points = [origin+a*x+b*y for a,b in local]
    _validate_profile(points,tol,"QS_Ende")
    for j in range(7):
        k = (j+1)%7
        corners = (start[j],start[k],points[j],points[k])
        vectors = [p-corners[0] for p in corners[1:]]
        normals = [rg.Vector3d.CrossProduct(vectors[a],vectors[b]) for a,b in ((0,1),(0,2),(1,2))]
        normal = max(normals,key=lambda n:n.Length)
        if normal.Length <= tol*max(v.Length for v in vectors):
            raise ValueError("Mantelflaeche {} ist degeneriert.".format(j))
        normal.Unitize()
        if any(abs(rg.Vector3d.Multiply(v,normal)) > tol for v in vectors):
            raise ValueError("Massvorgaben ergeben keine ebenen Mantelflaechen (Kante {}).".format(j))
        _validate_profile([start[j], start[k], points[k], points[j]], tol,
                          "Mantelflaeche {}".format(j))
    if bottom and any(abs(points[j].Z-start[j].Z) > tol for j in (3,4)):
        raise ValueError("Unten_Eben ist mit diesen Vorgaben nicht erfuellbar.")
    return points


def _calculate(inputs):
    import Rhino
    import Rhino.Geometry as rg
    doc = Rhino.RhinoDoc.ActiveDoc
    if doc is None:
        raise ValueError("Kein aktives Rhino-Dokument.")
    tol = doc.ModelAbsoluteTolerance
    g = inputs.get("G")
    curve = rg.LineCurve(g) if isinstance(g,rg.Line) else g
    if (not isinstance(curve,rg.Curve) or not curve.IsValid or curve.IsClosed
            or not curve.IsLinear(tol) or curve.GetLength() <= tol):
        raise ValueError("G: eine gueltige gerichtete gerade Linie erforderlich.")
    start = _read_start(inputs.get("QS_Start"), curve, tol)
    perpendicular = _boolean(inputs.get("Ende_Rechtwinklig"), "Ende_Rechtwinklig", True)
    bottom = _boolean(inputs.get("Unten_Eben"), "Unten_Eben", False)
    x,y,_ = _basis(curve, perpendicular)
    f = _number(inputs.get("Fahrbahnbreite"), "Fahrbahnbreite")
    if f <= tol:
        raise ValueError("Fahrbahnbreite: positiver Wert groesser Dokumenttoleranz erforderlich.")
    known = {}
    for slot in (1,) if bottom else (1,2):
        name = inputs.get("Wahl_Abmessung_" + str(slot))
        name = name.strip() if isinstance(name,str) else name
        if name not in _NAMES or (bottom and name == "Hoehe_2"):
            raise ValueError("Wahl_Abmessung_{}: unzulaessige Auswahl.".format(slot))
        index = _NAMES.index(name)
        if index in known:
            raise ValueError("Zwei verschiedene Abmessungen auswaehlen.")
        value = _number(inputs.get("Abmessung_"+str(slot)), name)
        if value <= tol:
            raise ValueError(name + ": positiver Wert groesser Dokumenttoleranz erforderlich.")
        known[index] = value
    unknown = set(range(4))-set(known)
    # Unbekannte werden auf eine typische Laenge normiert, um Gleichungen
    # mit sehr verschiedenen Dokumenteinheiten stabiler auszuwerten.
    scale = max(f, *known.values(), *(p.DistanceTo(start[0]) for p in start))
    dims = [{():known[i]/scale} if i in known else {(i,):1.0} for i in range(4)]
    origin = curve.PointAtEnd
    specs = ((None,0,None,0),(None,f/(2*scale),None,0),(0,0,1,0),(2,0,3,0),
             (2,0,3,0),(0,0,1,0),(None,-f/(2*scale),None,0))
    end = []
    for j,(bi,bconst,hi,hconst) in enumerate(specs):
        bp = {():bconst} if bi is None else {k:v*(0.5 if j in (2,3) else -0.5) for k,v in dims[bi].items()}
        hp = {():hconst} if hi is None else dims[hi]
        end.append([_add(_add({():c/scale}, {k:v*a for k,v in bp.items()}),
                              {k:v*b for k,v in hp.items()}, -1)
                    for c,a,b in zip((origin.X-start[0].X,origin.Y-start[0].Y,origin.Z-start[0].Z),
                                     (x.X,x.Y,x.Z),(y.X,y.Y,y.Z))])
    sp = [[(p.X-start[0].X)/scale,(p.Y-start[0].Y)/scale,(p.Z-start[0].Z)/scale] for p in start]
    equations = []
    for j in range(7):
        k = (j+1)%7
        u = [sp[k][a]-sp[j][a] for a in range(3)]
        v = [_add(end[j][a],{():sp[j][a]},-1) for a in range(3)]
        w = [_add(end[k][a],{():sp[j][a]},-1) for a in range(3)]
        eq = {}
        for a,b,c in ((0,1,2),(1,2,0),(2,0,1)):
            cross = _add(_mul(v[b],w[c]),_mul(v[c],w[b]),-1)
            eq = _add(eq,{key:value*u[a] for key,value in cross.items()})
        equations.append(eq)
    if bottom:
        for j in (3,4):
            equations.append(_add(end[j][2],{():sp[j][2]},-1))
    candidates = []
    failures = []
    for solved in _solve(equations, unknown):
        values = dict(known)
        values.update({i:v*scale for i,v in solved.items()})
        try:
            points = _end_geometry(start,origin,x,y,f,values,bottom,tol)
        except ValueError as exc:
            failures.append(str(exc))
            continue
        if not any(all(abs(values[i]-other[0][i]) <= tol for i in values)
                   for other in candidates):
            candidates.append((values,points))
    if not candidates:
        raise ValueError(failures[0] if failures else "Keine geometrisch gueltige Loesung.")
    if len(candidates) != 1:
        raise ValueError("Masskombination besitzt mehrere geometrisch gueltige Loesungen.")
    values,points = candidates[0]
    text = ["{}: {:.3f}".format(_NAMES[i],values[i]) for i in range(4) if i not in known]
    output = json.dumps({"xyz_points":[[p.X,p.Y,p.Z] for p in points]},indent=2,allow_nan=False)
    return text, output


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


def _run_component(inputs, report_error):
    from Grasshopper import DataTree
    from Grasshopper.Kernel.Data import GH_Path

    curves = _as_list(inputs.get("G"))
    starts = _as_list(inputs.get("QS_Start"))
    dimensions = DataTree[object]()
    ends = [None] * len(curves)
    if not curves:
        report_error("G: mindestens eine gerichtete gerade Linie erforderlich.")
    valid_lengths = len(starts) == len(curves)
    length_error = None
    if not valid_lengths:
        length_error = ("QS_Start: {} Eintraege fuer {} Kurven; genau ein QS je G erforderlich."
                        .format(len(starts), len(curves)))
        report_error(length_error)
        starts = [None] * len(curves)
    for index, curve in enumerate(curves):
        lines = ["Fehler: " + length_error] if length_error else None
        if valid_lengths:
            try:
                if starts[index] is None:
                    raise ValueError("QS_Start fehlt an diesem Index.")
                current = dict(inputs)
                current["G"] = curve
                current["QS_Start"] = starts[index]
                lines, ends[index] = _calculate(current)
            except Exception as exc:
                message = "G[{}]: {}".format(index, exc)
                report_error(message)
                lines = ["Fehler: " + message]
        path = GH_Path(index)
        for line in lines if lines else [None]:
            dimensions.Add(line, path)
    return dimensions, curves, starts, ends


if "ghenv" in globals():
    from Grasshopper.Kernel import GH_RuntimeMessageLevel

    def _report_error(message):
        ghenv.Component.AddRuntimeMessage(GH_RuntimeMessageLevel.Error, message)

    Abmessungen, G, QS_Start, QS_Ende = _run_component(globals(), _report_error)

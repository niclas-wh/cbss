# -*- coding: utf-8 -*-
"""SOFiMSHC-Geometrieexport -- Rhino 8 / Grasshopper / Python 3, Script-Modus.

Den gesamten Code in eine Python-3-Script-Komponente kopieren.
Eingaenge (Item Access): geo_path (str), lang (str: de/en), unit (str: m/mm),
                       geo_gdiv (positive ganze Zahl), debug (bool, optional).
Der bisherige Eingang gdiv heisst jetzt geo_gdiv; kein Fallback auf gdiv.
Bei debug einen Boolean Toggle anschliessen; ohne Wert gilt True.
debug=True: Pflichtvariablen-/Gruppen-/Strukturnummernpruefungen mit TXE/DBG.
debug=False: keine Pflichtvariablenpruefungen und keine Custom-Fehler in der DAT.
Die optionale Standardwert-Logik fuer grp und die Nummerierung bleiben aktiv.
Python-seitige Eingabe-/Geometrie-/Dateipruefungen bleiben ebenfalls aktiv.
Weitere Eingaenge beliebig hinzufuegen: geo_0, geo_1, geo_17, bc_0, bc_8, ...
geo_x und bc_x haben unabhaengige, lueckenlose ODER lueckenhafte Nummerierung.
ALLE geo_x/bc_x: Tree Access, kein Type Hint (Geometrie / No Type Hint).
geo_x und bc_x als Optional markieren, auch ohne Anschluss gueltig.
Damit wird pro Loesung die gesamte Datei einmal geschrieben, nicht pro Item.
Baumreihenfolge: Pfade, dann Items; Eingaenge nach numerischem x sortiert.
Leere Eingaenge, Null-Items und leere Listen werden ignoriert.
Ohne Geometrie endet der Export ohne Fehler; die Zieldatei bleibt unveraendert.
Ungueltige, nicht leere Geometrie bleibt ein Fehler.
Ausgabe: Standardausgang out (Status per print).
Nach erfolgreichem Dateiersatz: Dateipfad, lokaler Abschlusszeitstempel
(tt.mm.jjjj - hh:mm:ss), Statistiken je geo_x/bc_x, dann Hinweise zu Doppelungen.
Bei Fehlern oder leerer Geometrie wird kein Erfolgszeitstempel ausgegeben.

Akzeptiert: Linien/Kurven, Surface, BrepFace und offene Flaechen-Breps.
Mehrflaechige offene Breps erzeugen eine SAR je Face, in Face-Reihenfolge.
Geschlossene Volumen-Breps werden abgelehnt (keine implizite Schalenableitung).
Trimraender und Loecher bleiben als SARB erhalten, je Randsegment ein Satz.
Ebene Flaechen werden nur durch ihre Raender, Freiformen als NURBS exportiert.
Exakt deckungsgleiche ebene, geradlinig berandete Flaechen im selben geo_x
werden unabhaengig vom Umlaufsinn nur einmal exportiert (mit Statusmeldung).
Keine toleranzbasierte Zusammenfassung; keine Zusammenfassung ueber geo_x
hinweg, da dort andere Eigenschaften definiert sein koennen.
Teilueberlappungen sowie gekruemmte doppelte Flaechen werden nicht bereinigt.
Periodische NURBS werden am Parameterbereich formtreu geklemmt;
schlaegt diese Konvertierung fehl, wird nicht durch Polygone angenaehert.
Keine Koordinatenumrechnung: unit bezeichnet die Einheit der Eingangszahlen.
Dicken werden unveraendert als #t_x ohne angehaengte Einheit ausgegeben.
STO#t_x mit eigener Einheit definieren, z.B. STO#t_2 250[mm].
Ohne Einheit gelten fuer T die SOFiMSHC-Eingabeeinheiten, nicht unit.
Einzelsaetze stehen in einer Zeile; wiederholte Saetze bleiben Tabellen.
Flaechendaten sind eingerueckt; gerade Raender stehen als SARB ; SLNB ...
in einer Zeile. OUT wird als Standard weggelassen, IN bleibt explizit.
Vor jeder DAT-Kommentarzeile stehen zwei Leerzeilen, vor/nach LET#cbss_id eine.

Vor dem Include muessen die globalen STO-Variablen berechnet worden sein:
  Linie:   STO#qnr_1 10       (Material kommt aus dem AQUA-Querschnitt)
  Flaeche: STO#mat_2 1        und STO#t_2 250[mm]
  Optional fuer geo_2: STO#grp_2 4; ohne grp gilt lokal Gruppe 1.
  Pflicht fuer nichtleeres bc_8: STO#bc_8 'PZ'
geo_x erzeugt ausschliesslich Strukturgeometrie OHNE FIX. #fix_x wird nicht
mehr gelesen. Lagerungen kommen ausschliesslich aus bc_x / #BC_x.
bc_x akzeptiert Punkte (Point/Point3d), Kurven und dieselben Flaechen wie geo_x.
Alle geo_x werden zuerst geschrieben, dann alle bc_x nach numerischem x.
BC-Punkte: SPT ohne Nummer, anschliessend SPTP TYP/TYPE #BC_x GRP 0.
BC-Linien: SLN ohne Nummer mit GRP 0, QNR/SNO 0 und FIX #BC_x.
BC-Flaechen: SAR NR/NO PROP FIX #BC_x; kein Material, keine Dicke, keine
Gruppenaenderung an der vorhandenen Tragflaeche und keine zusaetzliche Steifigkeit.
BC-Geometrie muss die zu lagernde Traggeometrie raeumlich treffen.
SOFiMSHC nummeriert BC-Punkte/-Linien automatisch, unabhaengig von geo_gdiv.
BC-Geometrie wird weder dedupliziert noch auf Ueberlappung mit geo_x geprueft.
Es gibt KEINEN Ersatzwert fuer #bc_x. debug=False ueberlaesst fehlende
Pflichtvariablen der nativen SOFiSTiK-Fehlerbehandlung.
Existenzpruefung per LOOP#cbss_n DEF(name), danach IF #cbss_n==0.
Bei debug=True fuehren fehlende Pflichtvariablen zu TXE mit Namen und DBG# -2.
TXE nennt Namen ohne #, da CADINP sonst den Variablenwert einsetzt.
Eine leere STO-Zuweisung ist keine gueltige CADINP-Definition: optionale
Variablen stattdessen weglassen. Bereits gespeicherte STO-Werte ggf. loeschen.

Die Datei in einen eigenen SOFiMSHC-Block mit passender Sprache einbinden.
geo_gdiv hier bestimmt die Strukturnummern. SYST GDIV im Hauptprogramm bestimmt
hingegen die Nummernplaetze fuer die erzeugten FE-Elemente je Gruppe. Eine
SAR kann viele Tausend QUADs erzeugen. Fuer das FE-Netz muss dort ausreichend
Platz vorgesehen werden, unabhaengig von der Anzahl der GH-Flaechen.
Der Export aendert weder Vernetzungsdichte noch FE-Gruppenbasen.
Exportiert werden KEIN +PROG, ENDE, SYST oder STEU.
LET/IF/TXE/DBG sind nur CADINP-Pruefungen und Nummerierungslogik.
SLN: de NR/QNR, en NO/SNO; SAR: de NR/MNR, en NO/MNO.
FIX-Literale muessen zur Sprache des aufrufenden Programms passen.

Pro Gruppe werden Linien UND Flaechen gemeinsam fortlaufend nummeriert:
Gruppe 4 / geo_gdiv=1000: 4000...4999. Gruppe 0 beginnt bei 1, weil Nummer 0
in SOFiMSHC eine automatische Nummerierung ausloest. Ueberlauf wird bei
debug=True vor der Geometrieeingabe abgebrochen.
Nummern sind innerhalb dieses Exports eindeutig; bereits vorhandene Geometrie
im aufrufenden Modell wird nicht abgefragt. SOFiMSHC-Grenze: 99999.
Interne lokale Variablen cbss_g0/1/..., cbss_b0/1/..., cbss_id, cbss_n
und cbss_bad sind reserviert.
CADINP erlaubt hoechstens 16 Zeichen je Variablenname, also maximal 12 Ziffern
fuer geo_x (qnr_/mat_/grp_ + x), 13 Ziffern fuer bc_x (bc_ + x).
Keine fuehrenden Nullen ausser geo_0 bzw. bc_0.

Bestehende Datei wird erst nach vollstaendiger Geometriepruefung atomar ersetzt.
Der Zielordner muss existieren. Jede GH-Neuberechnung aktualisiert die Datei.
"""

from datetime import datetime
import math
import os
import re
import tempfile

import Rhino
import Rhino.Geometry as rg
import System


_INPUT_NAME = re.compile(r"^(geo|bc)_(0|[1-9][0-9]*)$")
_MAX_NUMBER = 99999


def _unwrap(value):
    for _ in range(4):
        if value is None:
            return None
        method = getattr(value, "ScriptVariable", None)
        if not callable(method):
            break
        next_value = method()
        if next_value is value:
            break
        value = next_value
    if isinstance(value, System.Guid):
        doc = Rhino.RhinoDoc.ActiveDoc
        value = doc.Objects.FindGeometry(value) if doc else None
    return value


def _text(value, name):
    value = _unwrap(value)
    if value is None:
        raise ValueError(name + ": Panel mit genau einem Wert erforderlich.")
    result = str(value).strip()
    if not result or len(result.splitlines()) != 1:
        raise ValueError(name + ": genau ein Wert erforderlich.")
    return result


def _boolean(value):
    value = _unwrap(value)
    if value is None:
        return True
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ("true", "1"):
        return True
    if text in ("false", "0"):
        return False
    raise ValueError("debug: Boolean Toggle oder true/false erwartet.")


def _integer(value, name):
    text = _text(value, name)
    try:
        number = float(text.replace(",", "."))
    except ValueError:
        raise ValueError(name + ": positive ganze Zahl erforderlich.")
    if not math.isfinite(number) or number != int(number) or number <= 0:
        raise ValueError(name + ": positive ganze Zahl erforderlich.")
    return int(number)


def _num(value):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("Geometrie enthaelt nicht endliche Zahlen.")
    return format(0.0 if value == 0 else value, ".17g")


def _xyz(point, unit):
    return tuple(_num(v) + "[" + unit + "]" for v in (point.X, point.Y, point.Z))


class _Writer:
    """Einzelsaetze inline, wiederholte Saetze als CADINP-Tabelle schreiben."""

    def __init__(self):
        self.lines = []
        self.schema = None
        self.rows = []
        self.indent = ""

    def _flush(self):
        if self.schema is None:
            return
        command, fields = self.schema
        if len(self.rows) == 1:
            tokens = [command]
            for field, value in zip(fields, self.rows[0]):
                tokens.extend((field, value))
            self.lines.append(self.indent + " ".join(tokens))
        else:
            self.lines.append(self.indent + command + " " + " ".join(fields))
            for row in self.rows:
                self.lines.append(self.indent + "    " + " ".join(row))
        self.schema = None
        self.rows = []

    def set_indent(self, spaces):
        self._flush()
        self.indent = " " * spaces

    def raw(self, text):
        self._flush()
        if text.lstrip().startswith("$"):
            self.lines.extend(("", ""))
        is_id = text.upper().startswith("LET#CBSS_ID ")
        if is_id:
            self.lines.append("")
        self.lines.append(self.indent + text if text else "")
        if is_id:
            self.lines.append("")

    def record(self, command, fields, values):
        schema = (command, tuple(fields))
        if schema != self.schema:
            self._flush()
            self.schema = schema
        self.rows.append(tuple(str(v) for v in values))

    def finish(self):
        self._flush()
        return "\n".join(self.lines) + "\n"


def _clamped(knots, degree):
    if knots.Count < 2 * degree:
        return False
    return (all(knots[i] == knots[0] for i in range(degree)) and
            all(knots[knots.Count - 1 - i] == knots[knots.Count - 1]
                for i in range(degree)))


def _curve_data(curve):
    if not curve.IsValid or curve.GetLength() <= 0:
        raise ValueError("Ungueltige Kurve oder Kurve ohne Laenge.")
    if isinstance(curve, rg.PolylineCurve):
        points = [curve.Point(i) for i in range(curve.PointCount)]
        return [("line", (a, b)) for a, b in zip(points, points[1:])
                if a.DistanceTo(b) > 0]
    if curve.IsLinear(1e-10):
        return [("line", (curve.PointAtStart, curve.PointAtEnd))]
    nurbs = curve.ToNurbsCurve()
    if nurbs is None:
        raise ValueError("Kurve kann nicht als NURBS exportiert werden.")
    if not _clamped(nurbs.Knots, nurbs.Degree):
        if not nurbs.Knots.ClampEnd(rg.CurveEnd.Both):
            raise ValueError("NURBS-Kurve kann nicht formtreu geklemmt werden.")
    if not nurbs.IsValid or not _clamped(nurbs.Knots, nurbs.Degree):
        raise ValueError("Ungueltige NURBS-Kurve nach Endklemmung.")
    return [("nurbs", nurbs)]


def _write_curve(writer, parts, unit, lang):
    for kind, data in parts:
        if kind == "line":
            writer.record("SLNB", ("X1", "Y1", "Z1", "X2", "Y2", "Z2"),
                          _xyz(data[0], unit) + _xyz(data[1], unit))
        else:
            for point in data.Points:
                writer.record("SLNP", ("TYP" if lang == "de" else "TYPE", "X", "Y", "Z", "W"),
                              ("NURB",) + _xyz(point.Location, unit) +
                              (_num(point.Weight),))
            for knot in data.Knots:
                writer.record("SLNN", ("S", "DEGR"), (_num(knot), data.Degree))


def _clamp_surface(surface):
    # Tensorprodukt: dieselbe homogene Kurvenoperation auf jede Kontrollreihe.
    for direction in (0, 1):
        knots = surface.KnotsU if direction == 0 else surface.KnotsV
        degree = surface.Degree(direction)
        if _clamped(knots, degree):
            continue
        count = surface.Points.CountU if direction == 0 else surface.Points.CountV
        rows = surface.Points.CountV if direction == 0 else surface.Points.CountU
        original_knots = list(knots)
        clamped_knots = None
        for row in range(rows):
            curve = rg.NurbsCurve(3, True, degree + 1, count)
            for i, knot in enumerate(original_knots):
                curve.Knots[i] = knot
            for i in range(count):
                u, v = (i, row) if direction == 0 else (row, i)
                curve.Points.SetPoint(i, surface.Points.GetControlPoint(u, v))
            if not curve.Knots.ClampEnd(rg.CurveEnd.Both):
                raise ValueError("NURBS-Flaeche kann nicht formtreu geklemmt werden.")
            if (not curve.IsValid or curve.Points.Count != count or
                    not _clamped(curve.Knots, degree)):
                raise ValueError("Ungueltige Kontrollreihe nach Endklemmung.")
            for i in range(count):
                u, v = (i, row) if direction == 0 else (row, i)
                surface.Points.SetControlPoint(u, v, curve.Points[i])
            clamped_knots = list(curve.Knots)
        for i, knot in enumerate(clamped_knots):
            knots[i] = knot
    if not surface.IsValid:
        raise ValueError("Ungueltige NURBS-Flaeche nach Endklemmung.")


def _face_data(face):
    surface = None
    if not face.IsPlanar(1e-8):
        surface = face.UnderlyingSurface().ToNurbsSurface()
        if surface is None or not surface.IsValid:
            raise ValueError("Flaeche kann nicht als NURBS exportiert werden.")
        _clamp_surface(surface)
    boundaries = []
    outer_count = 0
    for loop in face.Loops:
        if loop.LoopType == rg.BrepLoopType.Outer:
            kind = "OUT"
            outer_count += 1
        elif loop.LoopType == rg.BrepLoopType.Inner:
            kind = "IN"
        else:
            raise ValueError("Nicht unterstuetzter Trim-Loop: " + str(loop.LoopType))
        curve = loop.To3dCurve()
        if curve is None or not curve.IsClosed:
            raise ValueError("Offener oder ungueltiger Flaechenrand.")
        segments = curve.DuplicateSegments()
        if segments is None or len(segments) == 0:
            segments = [curve]
        for segment in segments:
            for part in _curve_data(segment):
                boundaries.append((kind, [part]))
    if outer_count != 1:
        raise ValueError("Je Flaeche wird genau ein geschlossener Aussenrand benoetigt.")
    u = face.Domain(0).Mid
    v = face.Domain(1).Mid
    normal = face.NormalAt(u, v)
    if face.OrientationIsReversed:
        normal.Reverse()
    if not normal.Unitize():
        raise ValueError("Flaechennormale ist nicht bestimmbar.")
    return surface, boundaries, normal


def _write_face(writer, data, unit, lang):
    surface, boundaries, _ = data
    typ = "TYP" if lang == "de" else "TYPE"
    writer.set_indent(4)
    if surface is not None:
        for u in range(surface.Points.CountU):
            for v in range(surface.Points.CountV):
                point = surface.Points.GetControlPoint(u, v)
                writer.record("SARP", (typ, "M", "N", "X", "Y", "Z", "W"),
                              ("NURB", u + 1, v + 1) + _xyz(point.Location, unit) +
                              (_num(point.Weight),))
        for knot in surface.KnotsU:
            writer.record("SARN", ("S", "DEGS"), (_num(knot), surface.Degree(0)))
        for knot in surface.KnotsV:
            writer.record("SARN", ("T", "DEGT"), (_num(knot), surface.Degree(1)))
    for kind, parts in boundaries:
        boundary = "SARB" if kind == "OUT" else "SARB " + typ + " " + kind
        if len(parts) == 1 and parts[0][0] == "line":
            a, b = parts[0][1]
            writer.raw(boundary + " ; SLNB " + "   ".join(_xyz(a, unit) + _xyz(b, unit)))
        else:
            writer.raw(boundary)
            _write_curve(writer, parts, unit, lang)
    writer.set_indent(0)


def _inputs(component):
    inputs = {"geo": [], "bc": []}
    seen = set()
    for param in component.Params.Input:
        name = str(param.NickName)
        if name in ("geo_path", "geo_gdiv") or not name.startswith(("geo_", "bc_")):
            continue
        match = _INPUT_NAME.fullmatch(name)
        if not match:
            raise ValueError(name + ": geo_0/bc_0, geo_1/bc_1, ... ohne fuehrende Nullen verwenden.")
        prefix, suffix = match.groups()
        if len(suffix) > (12 if prefix == "geo" else 13):
            raise ValueError(name + ": CADINP-Variablen duerfen maximal 16 Zeichen haben.")
        index = int(suffix)
        key = (prefix, index)
        if key in seen:
            raise ValueError("Doppelter Eingang: " + name)
        seen.add(key)
        if str(param.Access).lower() != "tree":
            raise ValueError(name + ": Tree Access einstellen (verhindert Dateinueberschreiben pro Item).")
        values = list(param.VolatileData.AllData(False))
        if values:
            inputs[prefix].append((index, name, values))
    return {prefix: sorted(items, key=lambda entry: entry[0])
            for prefix, items in inputs.items()}


def _planar_face_key(data):
    surface, boundaries, _ = data
    if surface is not None:
        return None
    edges = []
    for boundary_type, parts in boundaries:
        for kind, points in parts:
            if kind != "line":
                return None
            ends = tuple(sorted((point.X, point.Y, point.Z) for point in points))
            edges.append((boundary_type, ends))
    return tuple(sorted(edges))


def _geometry(inputs, boundary_conditions=False):
    groups = []
    notices = []
    for index, name, values in inputs:
        elements = []
        seen_faces = set()
        for item_index, value in enumerate(values):
            try:
                geometry = _unwrap(value)
                if geometry is None or (isinstance(geometry, (list, tuple)) and not geometry):
                    continue
                if boundary_conditions and isinstance(geometry, (rg.Point, rg.Point3d)):
                    point = geometry.Location if isinstance(geometry, rg.Point) else geometry
                    if not point.IsValid:
                        raise ValueError("Ungueltiger Lagerungspunkt.")
                    elements.append(("point", point))
                    continue
                if isinstance(geometry, rg.Line):
                    geometry = rg.LineCurve(geometry)
                if isinstance(geometry, rg.Curve):
                    elements.append(("line", _curve_data(geometry)))
                    continue
                if isinstance(geometry, rg.BrepFace):
                    faces = [geometry]
                elif isinstance(geometry, rg.Brep):
                    if not geometry.IsValid or geometry.IsSolid:
                        raise ValueError("Gueltiges offenes Flaechen-Brep erwartet, kein Volumen.")
                    faces = list(geometry.Faces)
                elif isinstance(geometry, rg.Surface):
                    brep = geometry.ToBrep()
                    if brep is None or not brep.IsValid:
                        raise ValueError("Ungueltige Surface.")
                    faces = list(brep.Faces)
                else:
                    expected = "Punkt, Linie/Kurve oder Flaeche" if boundary_conditions else "Linie/Kurve oder Flaeche"
                    raise ValueError(expected + " erwartet; erhalten: " + type(geometry).__name__)
                if not faces:
                    raise ValueError("Geometrie besitzt keine Flaechen.")
                for face_index, face in enumerate(faces):
                    data = _face_data(face)
                    key = None if boundary_conditions else _planar_face_key(data)
                    if key is not None:
                        if key in seen_faces:
                            notices.append("{} / Item {} / Face {}: exakt deckungsgleiche ebene Flaeche "
                                           "im selben Eingang uebersprungen.".format(name, item_index, face_index))
                            continue
                        seen_faces.add(key)
                    elements.append(("area", data))
            except Exception as exc:
                raise ValueError("{} / Item {}: {}".format(name, item_index, exc))
        if elements:
            groups.append((index, elements))
    return groups, notices


def _if_missing(writer, variable):
    writer.raw("LOOP#cbss_n DEF(" + variable + ")")
    writer.raw("ENDLOOP")
    writer.raw("IF #cbss_n==0")


def _abort(writer, condition, message):
    writer.raw("IF " + condition)
    writer.raw("TXE " + message)
    writer.raw("DBG# -2")
    writer.raw("ENDIF")


def _render(groups, bc_groups, lang, unit, divisor, debug):
    writer = _Writer()
    de = lang == "de"
    writer.raw("$ Grasshopper -> SOFiMSHC | unit=" + unit + " | geo_gdiv=" + str(divisor) +
               " | debug=" + str(debug).lower())
    writer.raw("$ " + ("geo_gdiv nummeriert Strukturelemente, nicht das FE-Netz."
                       if de else "geo_gdiv numbers structural elements, not the FE mesh."))
    if debug:
        writer.raw("LET#cbss_bad 0")
        for index, elements in groups:
            kinds = {kind for kind, _ in elements}
            required = (["qnr"] if "line" in kinds else []) + (["mat", "t"] if "area" in kinds else [])
            for prefix in required:
                variable = prefix + "_" + str(index)
                _if_missing(writer, variable)
                writer.raw("TXE " + (("Pflichtvariable fehlt: " if de else "Missing required variable: ") + variable))
                writer.raw("LET#cbss_bad 1")
                writer.raw("ENDIF")
        for index, _ in bc_groups:
            variable = "bc_" + str(index)
            _if_missing(writer, variable)
            writer.raw("TXE " + ("Pflichtvariable fehlt: " if de else "Missing required variable: ") + variable)
            writer.raw("LET#cbss_bad 1")
            writer.raw("ENDIF")
        _abort(writer, "#cbss_bad<>0", "Geometrieexport abgebrochen." if de else "Geometry export aborted.")
    for slot, (index, elements) in enumerate(groups):
        suffix = str(index)
        grp = "grp_" + suffix
        g = "#cbss_g" + str(slot)
        b = "#cbss_b" + str(slot)
        _if_missing(writer, grp)
        writer.raw("LET" + g + " 1")
        writer.raw("ELSE")
        writer.raw("LET" + g + " #" + grp)
        writer.raw("ENDIF")
        if debug:
            _abort(writer, "(" + g + "<0)|(" + g + "<>DIV(" + g + "))",
                   ("Ungueltige Gruppe: " if de else "Invalid group: ") + grp)
        writer.raw("LET" + b + " IIF(" + g + "==0,1,0)")
        for previous in range(slot):
            writer.raw("IF " + g + "==#cbss_g" + str(previous))
            writer.raw("LET" + b + " " + b + "+" + str(len(groups[previous][1])))
            writer.raw("ENDIF")
        if debug:
            _abort(writer, b + "+" + str(len(elements)) + ">" + str(divisor),
                   ("Strukturnummernbereich erschoepft bei geo_" if de else "Structural number range exhausted at geo_") + suffix)
            last = "{}*{}+{}+{}".format(g, divisor, b, len(elements) - 1)
            _abort(writer, last + ">" + str(_MAX_NUMBER),
                   ("Strukturnummer >99999 bei geo_" if de else "Structural number >99999 at geo_") + suffix)
    for slot, (index, elements) in enumerate(groups):
        suffix = str(index)
        g = "#cbss_g" + str(slot)
        b = "#cbss_b" + str(slot)
        writer.raw("$ geo_" + suffix)
        for offset, (kind, data) in enumerate(elements):
            # NR und GRP erlauben Literale: dort weder Arithmetik noch Arrayindizes.
            writer.raw("LET#cbss_id {}*{}+{}+{}".format(g, divisor, b, offset))
            if kind == "line":
                writer.record("SLN", ("NR" if de else "NO", "QNR" if de else "SNO", "GRP"),
                              ("#cbss_id", "#qnr_" + suffix, g))
                _write_curve(writer, data, unit, lang)
            else:
                normal = data[2]
                writer.record("SAR", ("NR" if de else "NO", "MNR" if de else "MNO", "T", "GRP", "NX", "NY", "NZ"),
                              ("#cbss_id", "#mat_" + suffix, "#t_" + suffix, g,
                               _num(normal.X), _num(normal.Y), _num(normal.Z)))
                _write_face(writer, data, unit, lang)
    for index, elements in bc_groups:
        writer.raw("$ bc_" + str(index))
        fix = "#BC_" + str(index)
        for kind, data in elements:
            if kind == "point":
                # Ohne NR wird ein vorhandener Punkt an dieser Stelle ueberlagert.
                writer.record("SPT", ("X", "Y", "Z"), _xyz(data, unit))
                writer.record("SPTP", ("TYP" if de else "TYPE", "GRP"), (fix, 0))
            elif kind == "line":
                # QNR/SNO=0: Lagerungslinie, kein zusaetzlicher steifer Stab.
                writer.record("SLN", ("GRP", "QNR" if de else "SNO", "FIX"), (0, 0, fix))
                _write_curve(writer, data, unit, lang)
            else:
                # PROP aendert nur FIX auf vorhandenen Flaechen, nicht deren Gruppe.
                writer.record("SAR", ("NR" if de else "NO", "FIX"), ("PROP", fix))
                _write_face(writer, data, unit, lang)
    return writer.finish()


def _export(namespace):
    path = os.path.abspath(os.path.expanduser(_text(namespace.get("geo_path"), "geo_path").strip('"')))
    if os.path.splitext(path)[1].lower() != ".dat":
        raise ValueError("geo_path: Dateiendung .dat erforderlich.")
    folder = os.path.dirname(path)
    if not os.path.isdir(folder):
        raise ValueError("Zielordner existiert nicht: " + folder)
    lang = _text(namespace.get("lang"), "lang").lower()
    unit = _text(namespace.get("unit"), "unit").lower()
    if lang not in ("de", "en"):
        raise ValueError("lang: de oder en erforderlich.")
    if unit not in ("m", "mm"):
        raise ValueError("unit: m oder mm erforderlich.")
    divisor = _integer(namespace.get("geo_gdiv"), "geo_gdiv")
    debug = _boolean(namespace.get("debug"))
    component = namespace["ghenv"].Component
    inputs = _inputs(component)
    groups, notices = _geometry(inputs["geo"])
    bc_groups, bc_notices = _geometry(inputs["bc"], boundary_conditions=True)
    if not groups and not bc_groups:
        print("Keine Geometrie vorhanden; Zieldatei bleibt unveraendert.")
        return
    text = _render(groups, bc_groups, lang, unit, divisor, debug)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=folder, prefix=".gh_geometry_", suffix=".tmp",
                                         delete=False) as stream:
            temporary = stream.name
            stream.write(text)
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None and os.path.exists(temporary):
            os.remove(temporary)
    completed_at = datetime.now().strftime("%d.%m.%Y - %H:%M:%S")
    print("Gespeichert: " + path)
    print(completed_at)
    for index, elements in groups:
        print("geo_{}: {} SLN, {} SAR".format(
            index, sum(kind == "line" for kind, _ in elements),
            sum(kind == "area" for kind, _ in elements)))
    for index, elements in bc_groups:
        print("bc_{}: {} Punkte, {} Linien, {} Attributsflaechen".format(
            index, sum(kind == "point" for kind, _ in elements),
            sum(kind == "line" for kind, _ in elements),
            sum(kind == "area" for kind, _ in elements)))
    for notice in notices + bc_notices:
        print(notice)


if "ghenv" in globals():
    try:
        _export(globals())
    except Exception as error:
        from Grasshopper.Kernel import GH_RuntimeMessageLevel
        ghenv.Component.AddRuntimeMessage(GH_RuntimeMessageLevel.Error, str(error))
        print("Export fehlgeschlagen; Zieldatei nicht ersetzt: " + str(error))

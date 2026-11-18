# -*- coding: utf-8 -*-
"""Startquerschnitt -- Rhino 8 / Grasshopper 1 / Python 3, Script-Modus.

Eingaenge:
  G: Curve Type Hint, LIST ACCESS; gerichtete gerade Linien (auch Rhino Line).
  Alle anderen Eingaenge: Item Access, gelten gemeinsam fuer alle G-Eintraege.
  Fahrbahnbreite, Breite_1, Breite_2, Hoehe_1, Hoehe_2: str Type Hint,
    positive endliche Gesamtbreiten/Tiefen in Rhino-Modelleinheiten.
  Rechtwinklig: str Type Hint, OPTIONAL (Required deaktivieren), Standard true.
Ausgaenge neben out: G (Liste unveraenderter Kurven), QS (Liste mit einem
XYZ-JSON je Kurve). Reihenfolge und Anzahl bleiben erhalten, bei Einzelfehlern
steht None am betreffenden Index. Leeres G liefert leere Listen und eine Meldung.
QS direkt an QS_Start (List Access) von section_profile anschliessen;
None-Eintraege nicht entfernen, da sonst die Indexzuordnung verloren geht.
Den alten Eingang Knotenpunkte entfernen. G bei section_profile anschliessen,
QS mit dessen QS_Start verbinden. Kein Import anderer Projektdateien notwendig.

Punkt 0 liegt am Anfang von G in Oberkantenmitte. Es folgen die Punkte
1=(F/2,0), 2=(B1/2,-H1), 3=(B2/2,-H2), 4=(-B2/2,-H2),
5=(-B1/2,-H1), 6=(-F/2,0) in lokalen Breiten-/Hoehenkoordinaten.
Der erste Punkt wird nicht wiederholt. Rechtwinklig=true: Profilebene normal
zur Tangente, Hoehenachse Welt-oben (bei vertikaler Linie Ersatz Welt-Y).
False: lotrechte Querebene mit Hoehenachse Welt-Z; nicht fuer vertikale G.
Ausgabe ausschliesslich {"xyz_points": [[x,y,z], ...]} in Weltkoordinaten.
Zahlenpanels akzeptieren Dezimalpunkt/-komma; bool auch als true/false-Text.
Ungueltige oder selbstschneidende Profile ergeben QS[i]=None und eine
Fehlermeldung mit Kurvenindex; die uebrigen Profile werden weiterverarbeitet.
"""

import json
import math


def _number(value, label):
    if isinstance(value, str):
        text = value.strip()
        if not text or len(text.splitlines()) != 1:
            raise ValueError(label + ": genau einen Zahlenwert im Panel eingeben.")
        try:
            value = float(text.replace(",", "."))
        except ValueError:
            raise ValueError(label + ": Zahl ohne Einheit erwartet, z.B. 2.5 oder 2,5.")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(label + ": endliche Zahl erforderlich.")
    try:
        value = float(value)
    except OverflowError:
        raise ValueError(label + ": Zahl ist zu gross.")
    if not math.isfinite(value):
        raise ValueError(label + ": endliche Zahl erforderlich.")
    return value


def _boolean(value):
    if value is None or (isinstance(value, str) and not value.strip()):
        return True
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text == "true":
            return True
        if text == "false":
            return False
    raise ValueError("Rechtwinklig: true oder false im Panel eingeben.")


def _frame(g, perpendicular):
    import Rhino
    import Rhino.Geometry as rg

    doc = Rhino.RhinoDoc.ActiveDoc
    if doc is None:
        raise ValueError("Kein aktives Rhino-Dokument.")
    tol = doc.ModelAbsoluteTolerance
    curve = rg.LineCurve(g) if isinstance(g, rg.Line) else g
    if (not isinstance(curve, rg.Curve) or not curve.IsValid or curve.IsClosed
            or not curve.IsLinear(tol) or curve.GetLength() <= tol):
        raise ValueError("G: eine gueltige gerichtete gerade Linie erforderlich.")
    tangent = curve.PointAtEnd - curve.PointAtStart
    tangent.Unitize()
    up = rg.Vector3d.ZAxis
    if perpendicular:
        y = up - tangent * rg.Vector3d.Multiply(up, tangent)
        if y.Length <= 1e-8:
            up = rg.Vector3d.YAxis
            y = up - tangent * rg.Vector3d.Multiply(up, tangent)
        y.Unitize()
        x = rg.Vector3d.CrossProduct(y, tangent)
    else:
        x = rg.Vector3d.CrossProduct(up, tangent)
        if x.Length <= 1e-12:
            raise ValueError("Rechtwinklig=false: vertikale Gradiente nicht definierbar.")
        y = up
    x.Unitize()
    return curve.PointAtStart, x, y, tol


def erstelle_qs(g, fahrbahnbreite, breite_1, breite_2,
                hoehe_1, hoehe_2, rechtwinklig=None):
    """Symmetrischen Startquerschnitt als globale XYZ-Koordinaten erzeugen."""
    f = _number(fahrbahnbreite, "Fahrbahnbreite")
    b1 = _number(breite_1, "Breite_1")
    b2 = _number(breite_2, "Breite_2")
    h1 = _number(hoehe_1, "Hoehe_1")
    h2 = _number(hoehe_2, "Hoehe_2")
    perpendicular = _boolean(rechtwinklig)
    for label, value in (("Fahrbahnbreite", f), ("Breite_1", b1),
                         ("Breite_2", b2), ("Hoehe_1", h1), ("Hoehe_2", h2)):
        if value <= 0:
            raise ValueError(label + ": ein positiver Wert erforderlich.")
    points = [
        [0.0, 0.0],
        [f/2, 0.0],
        [b1/2, -h1],
        [b2/2, -h2],
        [-b2/2, -h2],
        [-b1/2, -h1],
        [-f/2, 0.0],
    ]
    import Rhino.Geometry as rg

    origin, x, y, tol = _frame(g, perpendicular)
    world = [origin + a*x + b*y for a, b in points]
    for i, point in enumerate(world):
        if any(point.DistanceTo(other) <= tol for other in world[i+1:]):
            raise ValueError("QS: doppelte oder zu nahe Randpunkte.")
    profile = rg.PolylineCurve(world + [world[0]])
    if rg.Intersect.Intersection.CurveSelf(profile, tol).Count:
        raise ValueError("QS: Selbstschnitt oder ueberlappende Profilkanten.")
    caps = rg.Brep.CreatePlanarBreps(profile, tol)
    if not caps or len(caps) != 1 or not caps[0].IsValid:
        raise ValueError("QS: kein gueltiger ebener Querschnitt.")
    return json.dumps({"xyz_points": [[p.X, p.Y, p.Z] for p in world]},
                      indent=2, allow_nan=False)


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
    curves = _as_list(inputs.get("G"))
    results = []
    if not curves:
        report_error("G: mindestens eine gerichtete gerade Linie erforderlich.")
    for index, curve in enumerate(curves):
        try:
            result = erstelle_qs(
                curve, inputs.get("Fahrbahnbreite"),
                inputs.get("Breite_1"), inputs.get("Breite_2"),
                inputs.get("Hoehe_1"), inputs.get("Hoehe_2"),
                inputs.get("Rechtwinklig"))
        except Exception as exc:
            report_error("G[{}]: {}".format(index, exc))
            result = None
        results.append(result)
    return curves, results


# Import ohne Rhino fuer Logik-/Kompatibilitaetstests ermoeglichen.
if "ghenv" in globals():
    from Grasshopper.Kernel import GH_RuntimeMessageLevel

    def _report_error(message):
        ghenv.Component.AddRuntimeMessage(GH_RuntimeMessageLevel.Error, message)

    G, QS = _run_component(globals(), _report_error)

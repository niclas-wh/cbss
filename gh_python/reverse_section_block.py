# -*- coding: utf-8 -*-
"""Querschnittsreihenfolge umkehren -- Rhino 8 / GH 1 / Python 3 Script-Modus.

Den gesamten Code in die Python-3-Script-Komponente einfuegen.
Eingang: QS, str Type Hint, LIST ACCESS; XYZ-JSON aus den Querschnittsbloecken.
Ausgang neben out: QS_Reverse, Liste mit einem XYZ-JSON je Eingangseintrag.
Auch ein einzelner JSON-Text oder ein dict wird als ein Eintrag angenommen.

Neue Punktfolge: 0, 6, 5, 4, 3, 2, 1. Punkt 0 bleibt fest; Koordinaten werden
weder verschoben noch gespiegelt oder gerundet. Nur die Randreihenfolge wird
umgekehrt. Erwartet werden genau sieben Punkte ohne wiederholten Schlusspunkt
im Format {"xyz_points": [[x,y,z], ...]} in Rhino-Modelleinheiten.
Die Kurvenrichtung und Positionierung werden durch diesen Block nicht geaendert.

None bleibt als Platzhalter erhalten. Fehlerhafte Eintraege liefern None und
eine GH-Fehlermeldung mit QS-Index; andere Eintraege bleiben erhalten.
Die Listenreihenfolge bleibt unveraendert. Keine gemeinsamen Projektimporte.
"""

import json
import math


def reverse_section(value):
    if value is None:
        return None
    data = json.loads(value) if isinstance(value, str) else value
    if not isinstance(data, dict) or set(data) != {"xyz_points"}:
        raise ValueError('Ausschliesslich {"xyz_points": [...]} erwartet.')
    points = data["xyz_points"]
    if not isinstance(points, (list, tuple)) or len(points) != 7:
        raise ValueError("Genau sieben Randpunkte 0..6 erforderlich.")
    for index, point in enumerate(points):
        if not isinstance(point, (list, tuple)) or len(point) != 3:
            raise ValueError("Punkt {}: [x,y,z] erforderlich.".format(index))
        for coordinate in point:
            if (isinstance(coordinate, bool)
                    or not isinstance(coordinate, (int, float))
                    or not math.isfinite(coordinate)):
                raise ValueError("Punkt {}: endliche numerische Koordinaten erforderlich."
                                 .format(index))
    reversed_points = [points[0]] + list(reversed(points[1:]))
    return json.dumps({"xyz_points": reversed_points}, indent=2, allow_nan=False)


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, (str, dict)):
        return [value]
    try:
        return list(value)
    except TypeError:
        return [value]


def _run_component(value, report_error):
    results = []
    for index, section in enumerate(_as_list(value)):
        try:
            result = reverse_section(section)
        except Exception as exc:
            report_error("QS[{}]: {}".format(index, exc))
            result = None
        results.append(result)
    return results


if "ghenv" in globals():
    from Grasshopper.Kernel import GH_RuntimeMessageLevel

    def _report_error(message):
        ghenv.Component.AddRuntimeMessage(GH_RuntimeMessageLevel.Error, message)

    QS_Reverse = _run_component(globals().get("QS"), _report_error)

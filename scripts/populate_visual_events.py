#!/usr/bin/env python3
"""populate_visual_events.py — Add per-scene visual events to all scene JSONs.

Reads each scene JSON, adds historically-relevant visual_events based on
narration content and segment timings, writes back to the JSON.

Visual event types: callout (highlighted date/name), card (info box),
diagram (conceptual visual).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'output', 'scenes')


def seg_time(scene, seg_idx, offset=0.0):
    """Calculate absolute time in seconds for a point within a segment."""
    t = 0.0
    for i in range(seg_idx):
        t += scene['segments'][i].get('duration_s', 12.0)
    t += offset
    return t


def populate_scene_01(s):
    """Vor der Stadt — pre-1100 settlement at the Leine ford."""
    events = []
    # Seg 2 (12-24): Stone age / Bronze age settlement
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 1, 3.0), "duration": 6.0,
        "text": "5000+ Jahre", "subtext": "Durchgehende Besiedlung seit der Steinzeit",
        "position": "center", "anim": "pop", "style": "highlight",
        "anim_duration": 0.4,
    })
    # Seg 3 (24-36): Varusschlacht 9 AD
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 2, 2.0), "duration": 7.0,
        "text": "9 n. Chr.", "subtext": "Varusschlacht — Arminius vernichtet 3 Legionen",
        "position": "center", "anim": "pop", "style": "warning",
        "anim_duration": 0.5,
    })
    # Seg 5 (48-60): Saxons
    events.append({
        "type": "card", "trigger_time": seg_time(s, 4, 2.0), "duration": 7.0,
        "title": "Die Sachsen", "body": "Ostfalen — Engern — Westfalen\nLeinetal = Bereich der Engern",
        "position": "right", "anim": "slide_left", "anim_duration": 0.5,
    })
    # Seg 6 (60-72): Geography — Leine, Ihme, Eilenriede
    events.append({
        "type": "diagram", "trigger_time": seg_time(s, 5, 1.0), "duration": 8.0,
        "title": "Geografie der Leinefurth", "body": "Leine (Solling → Schwarmstedt)\nIhme → Leine (Stadtgebiet)\nEilenriede — 645 ha Stadtwald",
        "position": "left", "anim": "fade_in", "anim_duration": 0.6,
    })
    # Seg 7 (72-84): Trade routes
    events.append({
        "type": "diagram", "trigger_time": seg_time(s, 6, 2.0), "duration": 6.0,
        "title": "Handelsrouten", "body": "Ost-West: Harz → Leinetal → Weser → Nordsee\nNord-Süd: Küste → Fränkisches Reich",
        "position": "bottom", "anim": "slide_up", "anim_duration": 0.5,
    })
    # Seg 8 (84-96): Karl der Große
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 7, 2.0), "duration": 7.0,
        "text": "772–804", "subtext": "Karl der Große — Sachsenkriege",
        "position": "center", "anim": "pop", "style": "highlight",
        "anim_duration": 0.5,
    })
    events.append({
        "type": "card", "trigger_time": seg_time(s, 7, 6.0), "duration": 4.0,
        "title": "Klöster", "body": "Corvey (815) — Gandersheim (852)\nZentren der Missionierung",
        "position": "right", "anim": "slide_left", "anim_duration": 0.4,
    })
    return events


def populate_scene_02(s):
    """Die erste Erwähnung — 1100-1300."""
    events = []
    # Seg 1 (0-12): First mention 1150
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 0, 1.0), "duration": 6.0,
        "text": "1150", "subtext": "Erste Erwähnung als Honovere",
        "position": "center", "anim": "pop", "style": "highlight",
        "anim_duration": 0.5,
    })
    events.append({
        "type": "card", "trigger_time": seg_time(s, 0, 5.0), "duration": 5.0,
        "title": "Honovere", "body": "\"ho\" = hoch\n\"over\" = Ufer / Hügel\nErhöhte Lage am Leineufer",
        "position": "right", "anim": "slide_left", "anim_duration": 0.5,
    })
    # Seg 2 (12-24): Trade on the Leine
    events.append({
        "type": "diagram", "trigger_time": seg_time(s, 1, 2.0), "duration": 7.0,
        "title": "Handel an der Leine", "body": "Harz → Leine → Aller → Weser\nGüter aus Norden flussaufwärts\nUmschlag an der Furth",
        "position": "left", "anim": "fade_in", "anim_duration": 0.6,
    })
    # Seg 3 (24-36): Stadtrecht 1241
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 2, 3.0), "duration": 6.0,
        "text": "1241", "subtext": "Stadtrechte durch Herzog Otto I. das Kind",
        "position": "center", "anim": "pop", "style": "highlight",
        "anim_duration": 0.5,
    })
    # Seg 4 (36-48): Marktkirche 97m tower
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 3, 4.0), "duration": 5.0,
        "text": "97 m", "subtext": "Turm der Marktkirche St. Georgii et Jacobi",
        "position": "right", "anim": "slide_left", "style": "info",
        "anim_duration": 0.4,
    })
    # Seg 6 (60-72): Neighbors
    events.append({
        "type": "card", "trigger_time": seg_time(s, 5, 2.0), "duration": 7.0,
        "title": "Mächtige Nachbarn", "body": "Braunschweig — 70 km östlich\nHildesheim — 35 km südlich\nHannover: intermediäre Position",
        "position": "right", "anim": "slide_left", "anim_duration": 0.5,
    })
    # Seg 8 (84-96): Hanse connection
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 7, 5.0), "duration": 5.0,
        "text": "Hanse", "subtext": "14. Jh.: Verbindung zur Hanse",
        "position": "center", "anim": "fade_in", "style": "highlight",
        "anim_duration": 0.5,
    })
    return events


def populate_scene_03(s):
    """Das vierzehnte Jahrhundert — 1300-1400."""
    events = []
    # Seg 1 (0-12): City wall and gates
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 0, 2.0), "duration": 5.0,
        "text": "8 m hoch", "subtext": "Stadtmauer aus Bruchstein",
        "position": "left", "anim": "pop", "style": "highlight",
        "anim_duration": 0.4,
    })
    events.append({
        "type": "card", "trigger_time": seg_time(s, 0, 6.0), "duration": 5.0,
        "title": "Stadttore", "body": "Steintor (1314) — Norden\nLeintor (1340) — Westen\nAegidientor (1300) — Südosten\nBrühltor — viertes Tor",
        "position": "right", "anim": "slide_left", "anim_duration": 0.5,
    })
    # Seg 2 (12-24): Marktkirche tower
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 1, 3.0), "duration": 6.0,
        "text": "97,26 m", "subtext": "Marktkirche — Wahrzeichen der Stadt",
        "position": "center", "anim": "pop", "style": "highlight",
        "anim_duration": 0.5,
    })
    # Seg 4 (36-48): Hanse
    events.append({
        "type": "card", "trigger_time": seg_time(s, 3, 2.0), "duration": 7.0,
        "title": "Hansehandel", "body": "Stockfisch aus Norwegen\nTuche aus Flandern\nPelze aus dem Osten",
        "position": "left", "anim": "slide_right", "anim_duration": 0.5,
    })
    # Seg 5 (48-60): Rathaus 1410
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 4, 2.0), "duration": 5.0,
        "text": "ca. 1410", "subtext": "Neues Rathaus am Marktplatz",
        "position": "center", "anim": "pop", "style": "highlight",
        "anim_duration": 0.4,
    })
    # Seg 7 (72-84): Schwarzer Tod
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 6, 2.0), "duration": 7.0,
        "text": "1347–1353", "subtext": "Der Schwarze Tod — Pestpandemie",
        "position": "center", "anim": "pop", "style": "warning",
        "anim_duration": 0.5,
    })
    events.append({
        "type": "card", "trigger_time": seg_time(s, 6, 6.0), "duration": 5.0,
        "title": "Folgen der Pest", "body": "1/3 bis 1/2 der Bevölkerung Europas\nLöhne stiegen — Pacht neu verhandelt\nArbeiter konnten bessere Bedingungen durchsetzen",
        "position": "right", "anim": "slide_left", "anim_duration": 0.5,
    })
    return events


def populate_scene_04(s):
    """Die Welfen und Niedersachsen — 1400-1500."""
    events = []
    # Seg 1 (0-12): Welf dynasty
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 0, 2.0), "duration": 5.0,
        "text": "1235", "subtext": "Herzogtum Braunschweig-Lüneburg",
        "position": "center", "anim": "pop", "style": "highlight",
        "anim_duration": 0.5,
    })
    events.append({
        "type": "card", "trigger_time": seg_time(s, 0, 6.0), "duration": 5.0,
        "title": "Teilungen des Herzogtums", "body": "1269: Braunschweiger & Lüneburger Linie\n1409 & 1428: Mittlere Häuser",
        "position": "right", "anim": "slide_left", "anim_duration": 0.5,
    })
    # Seg 2 (12-24): Calenberg + Otto der Quade
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 1, 2.0), "duration": 5.0,
        "text": "1432", "subtext": "Fürstentum Calenberg gegründet",
        "position": "center", "anim": "pop", "style": "highlight",
        "anim_duration": 0.4,
    })
    events.append({
        "type": "card", "trigger_time": seg_time(s, 1, 6.0), "duration": 4.0,
        "title": "Otto der Quade", "body": "1367–1394 — \"der Böse\"\nHerzog von Braunschweig-Göttingen",
        "position": "left", "anim": "slide_right", "style": "warning",
        "anim_duration": 0.5,
    })
    # Seg 3 (24-36): Franziskanerkloster → Leineschloss
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 2, 2.0), "duration": 5.0,
        "text": "ca. 1300", "subtext": "Franziskanerkloster am Leineufer",
        "position": "left", "anim": "fade_in", "style": "info",
        "anim_duration": 0.5,
    })
    # Seg 4 (36-48): Residenzstadt 1636
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 3, 3.0), "duration": 6.0,
        "text": "1636", "subtext": "Herzog Georg → Hannover wird Residenzstadt",
        "position": "center", "anim": "pop", "style": "highlight",
        "anim_duration": 0.5,
    })
    return events


def populate_scene_05(s):
    """Reformation und Glaubensspaltung — 1500-1600."""
    events = []
    # Seg 1 (0-12): Reformation reaches Hannover
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 0, 1.0), "duration": 5.0,
        "text": "1524", "subtext": "Stadtrat erlässt Mandat gegen Lutheraner",
        "position": "center", "anim": "pop", "style": "warning",
        "anim_duration": 0.4,
    })
    # Seg 2 (12-24): Bürgereid 1533
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 1, 2.0), "duration": 6.0,
        "text": "26. Juni 1533", "subtext": "Bürgereid — Schwur auf die evangelische Lehre",
        "position": "center", "anim": "pop", "style": "highlight",
        "anim_duration": 0.5,
    })
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 1, 7.0), "duration": 4.0,
        "text": "\"am siden Faden\"", "subtext": "Bürgermeister Berckhusen über die Krise",
        "position": "bottom", "anim": "fade_in", "style": "warning",
        "anim_duration": 0.5,
    })
    # Seg 3 (24-36): Kirchenordnung 1536
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 2, 1.0), "duration": 5.0,
        "text": "1536", "subtext": "Kirchenordnung durch Urbanus Rhegius",
        "position": "center", "anim": "pop", "style": "highlight",
        "anim_duration": 0.4,
    })
    # Seg 5 (48-60): Schlacht bei Drakenburg
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 4, 5.0), "duration": 5.0,
        "text": "23. Mai 1547", "subtext": "Schlacht bei Drakenburg",
        "position": "left", "anim": "pop", "style": "warning",
        "anim_duration": 0.5,
    })
    events.append({
        "type": "card", "trigger_time": seg_time(s, 4, 8.0), "duration": 3.0,
        "title": "Siege der Protestanten", "body": "Einzig Triumph im\nSchmalkaldischen Krieg",
        "position": "right", "anim": "slide_left", "style": "highlight",
        "anim_duration": 0.3,
    })
    # Seg 6 (60-72): Augsburger Religionsfrieden
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 5, 1.0), "duration": 5.0,
        "text": "1555", "subtext": "Augsburger Religionsfriede",
        "position": "center", "anim": "pop", "style": "highlight",
        "anim_duration": 0.5,
    })
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 5, 7.0), "duration": 4.0,
        "text": "1576", "subtext": "Universität Helmstedt gegründet",
        "position": "right", "anim": "slide_left", "style": "info",
        "anim_duration": 0.4,
    })
    return events


def populate_scene_06(s):
    """Der Dreißigjährige Krieg — 1618-1648."""
    events = []
    # Seg 1 (0-12): War begins
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 0, 2.0), "duration": 6.0,
        "text": "23. Mai 1618", "subtext": "Prager Fenstersturz — Krieg beginnt",
        "position": "center", "anim": "pop", "style": "warning",
        "anim_duration": 0.5,
    })
    # Seg 2 (12-24): Tilly
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 1, 2.0), "duration": 5.0,
        "text": "25. Oktober 1625", "subtext": "Tilly besiegt Obentraut bei Seelze",
        "position": "center", "anim": "pop", "style": "warning",
        "anim_duration": 0.5,
    })
    events.append({
        "type": "card", "trigger_time": seg_time(s, 1, 6.0), "duration": 5.0,
        "title": "Tilly vor Hannover", "body": "Lager auf dem Lindener Berg\nAlle Städte Calenbergs besetzt\naußer Hannover — Stadt freikauft",
        "position": "left", "anim": "slide_right", "style": "warning",
        "anim_duration": 0.5,
    })
    # Seg 3 (24-36): Lutter am Barenberge
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 2, 5.0), "duration": 5.0,
        "text": "27. August 1626", "subtext": "Schlacht bei Lutter am Barenberge",
        "position": "center", "anim": "pop", "style": "warning",
        "anim_duration": 0.5,
    })
    # Seg 4 (36-48): Gustav Adolf + Georg von Calenberg
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 3, 3.0), "duration": 5.0,
        "text": "16. Nov. 1632", "subtext": "Tod Gustav Adolfs bei Lützen",
        "position": "left", "anim": "pop", "style": "warning",
        "anim_duration": 0.4,
    })
    # Seg 5 (48-60): Befestigungen
    events.append({
        "type": "diagram", "trigger_time": seg_time(s, 4, 2.0), "duration": 7.0,
        "title": "Bastionärbefestigung", "body": "Niederländisches Vorbild\n8 Bastionen + Kurtinen + Ravelins\nCalenberger Neustadt (1646)",
        "position": "right", "anim": "slide_left", "anim_duration": 0.6,
    })
    # Seg 6 (60-72): Pest und Leid
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 5, 3.0), "duration": 6.0,
        "text": "1623–1636", "subtext": "Pestepidemien in Hannover",
        "position": "center", "anim": "pop", "style": "warning",
        "anim_duration": 0.5,
    })
    # Seg 7 (72-84): Population loss
    events.append({
        "type": "card", "trigger_time": seg_time(s, 6, 2.0), "duration": 7.0,
        "title": "Bevölkerungsverlust", "body": "Städte: ~-25% Einwohner\nLand: ~-40% Einwohner\nHandel ruiniert, Kassen leer",
        "position": "right", "anim": "slide_left", "style": "warning",
        "anim_duration": 0.5,
    })
    # Seg 8 (84-96): Westfälischer Friede
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 7, 2.0), "duration": 7.0,
        "text": "24. Oktober 1648", "subtext": "Westfälischer Friede — Münster & Osnabrück",
        "position": "center", "anim": "pop", "style": "highlight",
        "anim_duration": 0.5,
    })
    return events


def populate_scene_07(s):
    """Wiederaufbau — 1648-1680."""
    events = []
    # Seg 1 (0-12): Wiederaufbau
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 0, 1.0), "duration": 5.0,
        "text": "1648", "subtext": "Westfälischer Friede — Beginn des Wiederaufbaus",
        "position": "center", "anim": "pop", "style": "highlight",
        "anim_duration": 0.5,
    })
    # Seg 2 (12-24): Georg Wilhelm
    events.append({
        "type": "card", "trigger_time": seg_time(s, 1, 2.0), "duration": 7.0,
        "title": "Georg Wilhelm", "body": "Zweiter Sohn Georgs von Calenberg\nReisender — hielt sich in Venedig auf\nRegierung ohne ihn\nLetzter \"Heideherzog\" in Celle (†1705)",
        "position": "right", "anim": "slide_left", "anim_duration": 0.5,
    })
    # Seg 3 (24-36): Johann Friedrich
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 2, 1.0), "duration": 5.0,
        "text": "1665–1679", "subtext": "Herzog Johann Friedrich regiert Calenberg",
        "position": "center", "anim": "pop", "style": "highlight",
        "anim_duration": 0.4,
    })
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 2, 6.0), "duration": 4.0,
        "text": "1666–1670", "subtext": "Hof- und Stadtkirche in der Neustadt",
        "position": "left", "anim": "fade_in", "style": "info",
        "anim_duration": 0.5,
    })
    # Seg 4 (36-48): Ernst August
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 3, 2.0), "duration": 6.0,
        "text": "1679", "subtext": "Ernst August erbt Calenberg",
        "position": "center", "anim": "pop", "style": "highlight",
        "anim_duration": 0.5,
    })
    events.append({
        "type": "card", "trigger_time": seg_time(s, 3, 6.0), "duration": 4.0,
        "title": "Ernst August", "body": "Bis 1662: Fürstbischof von Osnabrück\nPolitik: Machterweiterung\nStehendes Heer nach franz. Vorbild",
        "position": "right", "anim": "slide_left", "anim_duration": 0.4,
    })
    return events


def populate_scene_08(s):
    """Barockes Hannover — Ernst August und die Personalunion 1680-1714."""
    events = []
    # Seg 1 (0-12): Ernst August + Sophie
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 0, 1.0), "duration": 5.0,
        "text": "17. Okt. 1658", "subtext": "Heirat Ernst August & Sophie von der Pfalz",
        "position": "center", "anim": "pop", "style": "highlight",
        "anim_duration": 0.5,
    })
    events.append({
        "type": "card", "trigger_time": seg_time(s, 0, 6.0), "duration": 5.0,
        "title": "Sophie von der Pfalz", "body": "Tochter des \"Winterkönigs\" Friedrich V.\nElisabeth Stuart = englische Prinzessin\nEine der bedeutendsten dynastischen Verbindungen",
        "position": "right", "anim": "slide_left", "anim_duration": 0.5,
    })
    # Seg 2 (12-24): Primogenitur 1683
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 1, 2.0), "duration": 5.0,
        "text": "1683", "subtext": "Primogenitur gegen Widerstand durchgesetzt",
        "position": "center", "anim": "pop", "style": "highlight",
        "anim_duration": 0.4,
    })
    # Seg 3 (24-36): Großer Garten
    events.append({
        "type": "card", "trigger_time": seg_time(s, 2, 2.0), "duration": 7.0,
        "title": "Herrenhausen", "body": "Großer Garten — barocke Anlage\nSchloss = politischer Mittelpunkt\nVorbild: Versailles",
        "position": "left", "anim": "slide_right", "style": "highlight",
        "anim_duration": 0.6,
    })
    # Seg 4 (36-48): Kurfürstenwürde 1692
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 3, 3.0), "duration": 6.0,
        "text": "1692", "subtext": "9. Kurwürde — Kurfürstentum Hannover",
        "position": "center", "anim": "pop", "style": "highlight",
        "anim_duration": 0.5,
    })
    # Seg 5 (48-60): Act of Settlement
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 4, 2.0), "duration": 5.0,
        "text": "1701", "subtext": "Act of Settlement — Sophie als Thronanwärterin",
        "position": "center", "anim": "pop", "style": "highlight",
        "anim_duration": 0.5,
    })
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 4, 7.0), "duration": 4.0,
        "text": "8. Juni 1714", "subtext": "Sophie stirbt — 2 Monate vor der Krönung",
        "position": "bottom", "anim": "fade_in", "style": "warning",
        "anim_duration": 0.4,
    })
    # Seg 6 (60-72): Leibniz
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 5, 1.0), "duration": 5.0,
        "text": "1676–1714", "subtext": "Gottfried Wilhelm Leibniz in Hannover",
        "position": "center", "anim": "pop", "style": "info",
        "anim_duration": 0.5,
    })
    events.append({
        "type": "card", "trigger_time": seg_time(s, 5, 5.0), "duration": 5.0,
        "title": "Leibniz", "body": "Hofrat & Bibliothekar\nInfinitesimalrechnung\n\"Annales imperii occidentis Brunsvicensis\"",
        "position": "right", "anim": "slide_left", "anim_duration": 0.4,
    })
    return events


def populate_scene_09(s):
    """König Georg I. — 1714-1727."""
    events = []
    # Seg 1 (12-24): Act of Settlement + Georg travels to London
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 0, 2.0), "duration": 6.0,
        "text": "22. Juni 1701", "subtext": "Act of Settlement — Sophie als Thronanwärterin",
        "position": "center", "anim": "pop", "style": "highlight",
        "anim_duration": 0.5,
    })
    events.append({
        "type": "card", "trigger_time": seg_time(s, 0, 6.0), "duration": 5.0,
        "title": "Personalunion", "body": "Hannover + Großbritannien\nEin Herrscher, zwei Reiche\nBis 1837 verbunden",
        "position": "right", "anim": "slide_left", "anim_duration": 0.5,
    })
    # Seg 2 (24-36): Georg doesn't immediately travel, regents
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 1, 2.0), "duration": 6.0,
        "text": "18. Sept. 1714", "subtext": "Georg Ludwig besteigt den britischen Thron",
        "position": "center", "anim": "pop", "style": "highlight",
        "anim_duration": 0.5,
    })
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 1, 7.0), "duration": 4.0,
        "text": "Deutsche Kanzlei", "subtext": "Regierung Hannovers aus London",
        "position": "left", "anim": "fade_in", "style": "info",
        "anim_duration": 0.5,
    })
    # Seg 3 (36-48): Impact on Hannover — loss of court
    events.append({
        "type": "card", "trigger_time": seg_time(s, 2, 2.0), "duration": 7.0,
        "title": "Folgen für Hannover", "body": "Hof zieht nach London\nGrößter Arbeitgeber verschwindet\nStadt verliert politisches Zentrum",
        "position": "right", "anim": "slide_left", "style": "warning",
        "anim_duration": 0.5,
    })
    # Seg 4 (48-60): Economic impact — "hübsche Familien"
    events.append({
        "type": "diagram", "trigger_time": seg_time(s, 3, 2.0), "duration": 7.0,
        "title": "Neue Eliten", "body": "Handelsbourgeoisie übernimmt\n\u201eHübsche Familien\u201c formieren sich\nStädtische Selbstverwaltung stärkt sich",
        "position": "left", "anim": "fade_in", "anim_duration": 0.6,
    })
    # Seg 5 (60-72): Cultural exchange
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 4, 2.0), "duration": 5.0,
        "text": "Kultureller Austausch", "subtext": "Hannoversche Hofkultur → London",
        "position": "center", "anim": "pop", "style": "highlight",
        "anim_duration": 0.5,
    })
    events.append({
        "type": "card", "trigger_time": seg_time(s, 4, 7.0), "duration": 4.0,
        "title": "Britisch-Deutsche Verbindung", "body": "Architektur, Gartenkunst\nMilitärische Zusammenarbeit\nWirtschaftliche Integration",
        "position": "right", "anim": "slide_left", "anim_duration": 0.4,
    })
    return events


def populate_scene_10(s):
    """Hannover als Residenz — 1727-1760."""
    events = []
    # Seg 1 (12-24): Georg II. ascends both thrones
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 0, 1.0), "duration": 5.0,
        "text": "1727", "subtext": "Georg II. — König & Kurfürst",
        "position": "center", "anim": "pop", "style": "highlight",
        "anim_duration": 0.5,
    })
    events.append({
        "type": "card", "trigger_time": seg_time(s, 0, 5.0), "duration": 5.0,
        "title": "Georg II.", "body": "Letzter britischer Monarch\nder personally im Heer anführte\nSchlacht bei Dettingen (1743)",
        "position": "right", "anim": "slide_left", "anim_duration": 0.5,
    })
    # Seg 2 (24-36): Georgia Augusta Universität Göttingen 1737
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 1, 2.0), "duration": 6.0,
        "text": "1737", "subtext": "Georgia Augusta — Universität Göttingen gegründet",
        "position": "center", "anim": "pop", "style": "highlight",
        "anim_duration": 0.5,
    })
    events.append({
        "type": "card", "trigger_time": seg_time(s, 1, 7.0), "duration": 4.0,
        "title": "Universität Göttingen", "body": "Enlightenment ideals\nFirst university with no religious test\nBecame a European intellectual hub",
        "position": "left", "anim": "slide_right", "style": "highlight",
        "anim_duration": 0.4,
    })
    # Seg 3 (36-48): Baroque music culture
    events.append({
        "type": "card", "trigger_time": seg_time(s, 2, 2.0), "duration": 7.0,
        "title": "Barocke Musikkultur", "body": "Oper, Theater, Ballett\nHöfische Repräsentation\nHannover als kulturelles Zentrum",
        "position": "right", "anim": "slide_left", "anim_duration": 0.5,
    })
    # Seg 4 (48-60): Architecture and "hübsche Familien"
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 3, 3.0), "duration": 6.0,
        "text": "Hübsche Familien", "subtext": "Bauaufstieg des Bürgertums",
        "position": "center", "anim": "pop", "style": "highlight",
        "anim_duration": 0.5,
    })
    # Seg 5 (60-72): Diplomacy + Seven Years' War
    events.append({
        "type": "callout", "trigger_time": seg_time(s, 4, 2.0), "duration": 5.0,
        "text": "Siebenjähriger Krieg", "subtext": "1756–1763 — Hannover in Gefahr",
        "position": "center", "anim": "pop", "style": "warning",
        "anim_duration": 0.5,
    })
    events.append({
        "type": "card", "trigger_time": seg_time(s, 4, 6.0), "duration": 5.0,
        "title": "Kriegsfolgen", "body": "Kurhannover besetzt (1757)\nConvention of Kloster Zeven\nSchlacht bei Minden (1759)",
        "position": "left", "anim": "slide_right", "style": "warning",
        "anim_duration": 0.5,
    })
    return events


POPULATORS = {
    1: populate_scene_01,
    2: populate_scene_02,
    3: populate_scene_03,
    4: populate_scene_04,
    5: populate_scene_05,
    6: populate_scene_06,
    7: populate_scene_07,
    8: populate_scene_08,
    9: populate_scene_09,
    10: populate_scene_10,
}


def main():
    total_events = 0
    for num in sorted(POPULATORS):
        path = os.path.join(OUTPUT_DIR, f"scene_{num:02d}.json")
        if not os.path.isfile(path):
            print(f"  Skipping scene {num}: file not found")
            continue

        with open(path) as f:
            scene = json.load(f)

        new_events = POPULATORS[num](scene)
        # Merge: keep existing events (e.g. image-type), add new text events
        existing = scene.get("visual_events", [])
        # Skip if scene already has non-image events (idempotent)
        existing_text = [e for e in existing if e.get("type") != "image"]
        if existing_text:
            print(f"  Scene {num} ({scene.get('title', '?')}): already has {len(existing_text)} text events, skipping")
            continue
        scene["visual_events"] = existing + new_events

        with open(path, 'w') as f:
            json.dump(scene, f, indent=2, ensure_ascii=False)

        total_events += len(new_events)
        print(f"  Scene {num} ({scene.get('title', '?')}): {len(new_events)} text events added, {len(scene['visual_events'])} total")

    print(f"\nTotal: {total_events} visual events across {len(POPULATORS)} scenes")


if __name__ == "__main__":
    main()

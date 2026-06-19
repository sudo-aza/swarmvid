#!/usr/bin/env python3
"""
generate_scenes.py — Generate all 28 scene JSON files for "Die Geschichte Hannovers".

Each scene JSON follows the format expected by render_scene.py:
{
  "scene_num": int,
  "title": str,
  "subtitle": str,
  "era": str,
  "segments": [{"text": str, "duration_s": float}, ...],
  "sources": [str, ...],
  "gradient": [str, ...],
  "accent": str
}

All narration text is in German. Each segment is kept under 1024 characters
for TTS API compatibility. Durations are estimated based on German speech
rate (~120 words/min ≈ 2 words/second).
"""

import json
import os
import math

SCENES_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts", "scenes")


def estimate_duration(text: str) -> float:
    """Estimate speech duration in seconds for German narration.
    German averages ~2.0-2.2 words per minute at documentary pace (~130 wpm).
    Add 1.5s padding per segment for natural pauses.
    """
    words = len(text.split())
    seconds = words / 2.15  # ~130 wpm
    return round(seconds + 1.5, 1)


def scene_colors(scene_num: int) -> dict:
    """Return gradient and accent colors for each scene.
    Cycles through color palettes to give visual variety.
    """
    palettes = [
        {"gradient": ["#0d1b2a", "#1b263b", "#415a77"], "accent": "#778da9"},  # Deep blue - prehistoric
        {"gradient": ["#1a1a2e", "#16213e", "#0f3460"], "accent": "#e94560"},  # Dark blue - medieval
        {"gradient": ["#2d132c", "#801336", "#c72c41"], "accent": "#ee4540"},  # Crimson - gothic
        {"gradient": ["#1b1a17", "#3a3932", "#5d5c55"], "accent": "#d4af37"},  # Gold - Welf period
        {"gradient": ["#2b2d42", "#3d405b", "#8d99ae"], "accent": "#ef233c"},  # Slate - reformation
        {"gradient": ["#0b0c10", "#1f2833", "#45a29e"], "accent": "#66fcf1"},  # Teal - war
        {"gradient": ["#1a1423", "#3c2a4a", "#6b4c7a"], "accent": "#c9a0dc"},  # Purple - baroque
        {"gradient": ["#0a1628", "#1a3a5c", "#2a6f97"], "accent": "#f4a261"},  # Ocean - 18th c.
        {"gradient": ["#132a13", "#1e4d2b", "#2d6a4f"], "accent": "#95d5b2"},  # Forest - Enlightenment
        {"gradient": ["#2b0a0a", "#5c1a1a", "#8b3a3a"], "accent": "#ff6b6b"},  # Red - revolution
        {"gradient": ["#1a1a2e", "#16213e", "#e2e2e2"], "accent": "#ffd700"},  # Royal - kingdom
        {"gradient": ["#0d1b2a", "#1b2838", "#2a475e"], "accent": "#c7d5e0"},  # Steel - Prussian
        {"gradient": ["#1a0a00", "#3d1f00", "#6b3a00"], "accent": "#e8a838"},  # Amber - industrial
        {"gradient": ["#0f0f0f", "#1a1a1a", "#333333"], "accent": "#ff4444"},  # Dark - WWI
        {"gradient": ["#1a1a2e", "#2d2d44", "#4a4a6a"], "accent": "#ffd700"},  # Weimar
        {"gradient": ["#1a0000", "#330000", "#660000"], "accent": "#cc0000"},  # Nazi - dark red
        {"gradient": ["#0a0a0a", "#1a1a1a", "#2a2a2a"], "accent": "#ff6600"},  # Destruction - WWII
        {"gradient": ["#2a1a0a", "#4a3a2a", "#6a5a4a"], "accent": "#d4a574"},  # Rubble - postwar
        {"gradient": ["#1a2a3a", "#2a4a5a", "#3a6a7a"], "accent": "#64ffda"},  # Modern - rebuild
        {"gradient": ["#1a1a2e", "#2a2a4e", "#3a3a6e"], "accent": "#ff69b4"},  # Culture
        {"gradient": ["#0a1a2a", "#1a3a5a", "#2a5a8a"], "accent": "#00ccff"},  # EXPO
        {"gradient": ["#0a1628", "#162844", "#2a4a6a"], "accent": "#4ecdc4"},  # Contemporary
        {"gradient": ["#1a1a2e", "#16213e", "#0f3460"], "accent": "#e94560"},  # Epilog
    ]
    idx = (scene_num - 1) % len(palettes)
    return palettes[idx]


# ─────────────────────────────────────────────────────────────────────────────
# SCENE 1: Vor der Stadt — Siedlung an der Leine (pre-1100)
# ─────────────────────────────────────────────────────────────────────────────
scene_1 = {
    "scene_num": 1,
    "title": "Vor der Stadt",
    "subtitle": "Siedlung an der Leine",
    "era": "vor 1100",
    "segments": [
        {
            "text": "Die Geschichte Hannovers beginnt lange vor der ersten Stadtmauer, lange vor dem ersten Marktplatz. Um die Leine herum, einem der vielen Flüsse, die durch die norddeutsche Tiefebene fließen, fanden sich schon in vorgeschichtlicher Zeit Menschen ein.",
            "duration_s": 15.0,
        },
        {
            "text": "Die geografische Lage war entscheidend. Die Leine, ein Nebenfluss der Aller, bot eine natürliche Furtstelle und damit einen strategischen Kreuzungspunkt für Handel und Reiseverkehr. Die fruchtbaren Schwemmebenen des Flusses versorgten die Siedler mit Ackerland und Weide.",
            "duration_s": 16.0,
        },
        {
            "text": "Archäologische Funde belegen eine Besiedlung der Region seit der Steinzeit. In der Bronzezeit und Eisenzeit ließen sich germanische Stämme in der Umgebung nieder. Die Cherusker, berühmt durch den Cheruskerfürsten Arminius, bewohnten Teile Niedersachsens.",
            "duration_s": 15.0,
        },
        {
            "text": "Während der römischen Kaiserzeit lag die Region jenseits des Limes, der festen Grenze des Römischen Reiches. Die Römer drachten bis an die Weser und Elbe vor, doch blieb das Gebiet der Leine frei von dauerhafter römischer Besatzung. Dieser Umstand prägte die kulturelle Eigenständigkeit.",
            "duration_s": 16.0,
        },
        {
            "text": "Im frühen Mittelalter siedelten sich die Sachsen im Bereich der mittleren und unteren Leine an. Sie betrieben Ackerbau und Viehzucht und handelten mit benachbarten Stämmen. Die christianisierung erreichte die Region im achten und neunten Jahrhundert durch karolingische Missionare.",
            "duration_s": 16.0,
        },
        {
            "text": "Die Landschaft um die heutige Stadt war reich an Wäldern, Mooren und Flussauen. Die Ihme, ein kleiner Nebenfluss, mündete nahe der späteren Siedlung in die Leine. Der Eilenriede, einer der größten Stadtwälder Europas, bot Holz, Wild und Schutz. Diese natürlichen Ressourcen machten den Ort ideal für eine dauerhafte Besiedlung.",
            "duration_s": 17.0,
        },
    ],
    "sources": [
        "Hannover Chronik, Stadtarchiv Hannover",
        "Widemann, Geschichte der Stadt Hannover (1880)",
    ],
    **scene_colors(1),
}

# ─────────────────────────────────────────────────────────────────────────────
# SCENE 2: Die erste Erwähnung und das Mittelalter (1100-1300)
# ─────────────────────────────────────────────────────────────────────────────
scene_2 = {
    "scene_num": 2,
    "title": "Die erste Erwähnung",
    "subtitle": "und das Mittelalter",
    "era": "1100–1300",
    "segments": [
        {
            "text": "Die erste urkundliche Erwähnung des Namens Hannover stammt aus dem Jahr elfhundertfünfzig. In einer Urkunde Kaiser Friedrichs Barbarossa erscheint der Ort als Honovere. Der Name bedeutet hoher Uferort und verweist auf die erhöhte Lage der Siedlung am Leineufer.",
            "duration_s": 16.0,
        },
        {
            "text": "Die Siedlung entwickelte sich aus einer kleinen Furtstelle zu einem Marktflecken. Die Leine diente als wichtiger Handelsweg, der den Ostwestverkehr mit dem Nord-Süd-Handel verband. Kaufleute und Handwerker siedelten sich entlang der Uferstraßen an.",
            "duration_s": 15.0,
        },
        {
            "text": "Im zwölften und dreizehnten Jahrhundert wuchs Hannover stetig. Marktrechte wurden verliehen, und die Siedlung erhielt erste städtische Privilegien. Eine feste Brücke über die Leine erleichterte den Handel erheblich. Der beginnende Bau der Marktkirche zeugte von wachsendem Wohlstand.",
            "duration_s": 16.0,
        },
        {
            "text": "Zünfte und Gilden entstanden. Schmiede, Weber, Bäcker und Töpfer organisierten sich und regelten ihr Handwerk. Die Merchantalklasse bildete die Grundlage einer bürgerlichen Selbstverwaltung. Ein Rat der Ältesten übernahm zunehmend städtische Aufgaben.",
            "duration_s": 15.0,
        },
        {
            "text": "Die Beziehungen zu den Nachbarstädten waren vielfältig. Braunschweig im Osten und Hildesheim im Süden waren mächtige Konkurrenten und Handelspartner zugleich. Hannover lag im Einflussbereich der Welfen, der mächtigen Herzöge, die über große Teile Niedersachsens herrschten.",
            "duration_s": 16.0,
        },
        {
            "text": "Erste Verteidigungsanlagen entstanden. Palisaden und Erdwälle schützten die wachsende Siedlung vor feindlichen Übergriffen. Die strategische Lage an der Leine machte diese Schutzmaßnahmen notwendig. Die Grundlagen der späteren Stadtmauer waren gelegt.",
            "duration_s": 14.0,
        },
    ],
    "sources": [
        "Urkundenbuch der Stadt Hannover, Stadtarchiv",
        "Hans-Claus Riepe, Kleine Geschichte Hannovers (2013)",
    ],
    **scene_colors(2),
}

# ─────────────────────────────────────────────────────────────────────────────
# SCENE 3: Stadtmauern, Kirchen und das gotische Hannover (1300-1400)
# ─────────────────────────────────────────────────────────────────────────────
scene_3 = {
    "scene_num": 3,
    "title": "Stadtmauern, Kirchen",
    "subtitle": "und das gotische Hannover",
    "era": "1300–1400",
    "segments": [
        {
            "text": "Im vierzehnten Jahrhundert erlebte Hannover einen bedeutenden Ausbau. Die Stadtmauer wurde errichtet und mit Toren und Türmen versehen. Das Leintor, das Aegidientor und das Steintor bildeten die Hauptzugänge zur Stadt. Innerhalb der Mauern verdichtete sich das städtische Leben.",
            "duration_s": 16.0,
        },
        {
            "text": "Der Bau großer Kirchen prägte das Stadtbild. Die Marktkirche am alten Marktplatz wurde zur wichtigsten Pfarrkirche. Die Aegidienkirche, die Kreuzkirche und weitere Gotteshäuser entstanden in gotischem Stil. Diese Kirchen waren nicht nur Orte des Glaubens, sondern auch soziale Zentren.",
            "duration_s": 16.0,
        },
        {
            "text": "Hannover schloss sich der Hanse an, wenn auch als sekundäre Mitgliedsstadt. Der Handel über die Leine und die Landwege florierte. Hanseatische Kaufleute brachten Waren aus den Baltischen und Nordseegebieten in die Stadt. Tuche, Salz, Holz und Fische wurden gehandelt.",
            "duration_s": 15.0,
        },
        {
            "text": "Das Rathaus wurde gebaut und diente als Sitz der städtischen Verwaltung. Hier tagte der Rat, wurden Gesetze erlassen und Streitigkeiten geschlichtet. Die Stadtverwaltung wurde immer professioneller. Stadtschreiber und Kämmerer sorgten für eine geordnete Führung.",
            "duration_s": 14.0,
        },
        {
            "text": "Die soziale Struktur der Stadt spiegelte sich in den Vierteln wider. Patrizier wohnten nahe dem Markt, Handwerker in den Gassen der Altstadt. Die große Pestilenz, der Schwarze Tod, erreichte Hannover und raffte einen großen Teil der Bevölkerung dahin. Die Folgen waren verheerend.",
            "duration_s": 15.0,
        },
        {
            "text": "Nach der Pest erholte sich die Stadt langsam. Die überlebenden Bewohner übernahmen Häuser und Werkstätten der Verstorbenen. Neue städtische Aufzeichnungen begannen. Die Stadt trat in eine Phase des langsamen, aber stetigen Wachstums ein, die bis in die frühe Neuzeit anhielt.",
            "duration_s": 16.0,
        },
    ],
    "sources": [
        "Grote, Hannoversche Geschichten (1900)",
        "Stadtarchiv Hannover, Bestand Kirchenbauakten",
    ],
    **scene_colors(3),
}

# ─────────────────────────────────────────────────────────────────────────────
# SCENE 4: Die Welfen kommen — Residenzstadt wird (1400-1500)
# ─────────────────────────────────────────────────────────────────────────────
scene_4 = {
    "scene_num": 4,
    "title": "Die Welfen kommen",
    "subtitle": "Residenzstadt wird",
    "era": "1400–1500",
    "segments": [
        {
            "text": "Das Haus Welf, eine der ältesten und mächtigsten Dynastien Europas, sollte die Geschicke Hannovers für Jahrhunderte bestimmen. Die Welfen stammten aus dem schwäbischen Raum und hatten sich im Laufe des Mittelalters zu Herzögen von Braunschweig-Lüneburg entwickelt.",
            "duration_s": 16.0,
        },
        {
            "text": "Herzog Otto der Quade, so genannt wegen seiner wechselnden Bündnisse, wählte Hannover als Residenz. Diese Entscheidung veränderte die Stadt grundlegend. Als Residenzstadt zog Hannover Adelige, Beamte und Künstler an. Die Bevölkerung wuchs, und der Wohlstand nahm zu.",
            "duration_s": 15.0,
        },
        {
            "text": "Das Leineschloss, die herzogliche Residenz, entstand am Ufer der Leine. Es sollte für Jahrhunderte das Machtzentrum der Welfen in Hannover bleiben. Von hier aus verwalteten die Herzöge ihre Ländereien, hielten Hof und empfingen ausländische Gesandten.",
            "duration_s": 15.0,
        },
        {
            "text": "Die Hofkultur veränderte das städtische Leben. Die herzogliche Verwaltung brauchte Juristen, Schreiber und Kleriker. Eine gebildete Elite entstand. Handwerker und Kaufleute profitierten von der Nachfrage des Hofes nach Luxusgütern und Dienstleistungen.",
            "duration_s": 15.0,
        },
        {
            "text": "Das Verhältnis zwischen den Welfenherzögen und der städtischen Bürgerschaft war nicht immer spannungsfrei. Der Rat der Stadt verteidigte städtische Privilegen gegen herzogliche Eingriffe. Steuerfragen, Gerichtsbarkeit und Marktregulierungen waren ständige Konfliktpunkte.",
            "duration_s": 15.0,
        },
        {
            "text": "Hannover wuchs in politischer Bedeutung. Die Welfen stellten den dynastischen Rahmen zur Verfügung, innerhalb dessen die Stadt sich entwickeln konnte. Der Grundstein für Hannovers Aufstieg zu einer der bedeutendsten Städte Norddeutschlands war gelegt.",
            "duration_s": 14.0,
        },
    ],
    "sources": [
        "Dunken, Die Welfen und ihr Braunschweiger Land (2014)",
        "Kleine Niedersächsische Literaturgeschichte",
    ],
    **scene_colors(4),
}

# ─────────────────────────────────────────────────────────────────────────────
# SCENE 5: Reformation und Glaubensspaltung (1500-1600)
# ─────────────────────────────────────────────────────────────────────────────
scene_5 = {
    "scene_num": 5,
    "title": "Reformation",
    "subtitle": "und Glaubensspaltung",
    "era": "1500–1600",
    "segments": [
        {
            "text": "Die Reformation erreichte Hannover in den zwanziger Jahren des sechzehnten Jahrhunderts. Luthers Schriften fanden rasch Verbreitung in der Stadt. Prediger und Gelehrte wandten sich der neuen Lehre zu. Die Marktkirche wurde zum Zentrum der lutherischen Bewegung in Hannover.",
            "duration_s": 16.0,
        },
        {
            "text": "Die Einführung der Reformation verlief in Hannover weitgehend friedlich. Anders als in manchen anderen Städten gab es keine iconoklastischen Ausschreitungen. Der Rat der Stadt unterstützte den Wechsel zur protestantischen Lehre. Herzog Ernst der Bekenner festigte den lutherischen Glauben im Fürstentum.",
            "duration_s": 16.0,
        },
        {
            "text": "Die Aegidienkirche und andere Kirchen wurden reformiert. Altäre wurden entfernt, Predigten in deutscher Sprache eingeführt. Der christliche Glaube sollte nun jedem Gläubigen direkt zugänglich sein, nicht mehr nur durch die Vermittlung der lateinischen Messe.",
            "duration_s": 15.0,
        },
        {
            "text": "Doch die Glaubensspaltung brachte auch Spannungen. Im Schmalkaldischen Krieg standen die protestantischen Fürsten gegen Kaiser Karl den Fünften. Hannover lag im Spannungsfeld der Konflikte. Die Gegenreformation fand in der Stadt kaum Anhänger.",
            "duration_s": 15.0,
        },
        {
            "text": "Eine kleine reformierte Gemeinde existierte neben der lutherischen Mehrheit. Die Koexistenz verschiedener Konfessionen war nicht immer einfach, doch in Hannover blieben die religiösen Konflikte vergleichsweise moderat. Die Stadt erwarb sich den Ruf der Toleranz.",
            "duration_s": 15.0,
        },
        {
            "text": "Die Reformation formte Hannovers Identität nachhaltig. Die Stadt wurde zu einem Zentrum des protestantischen Bildungswesens. Schulen wurden gegründet, das Kirchenlied gepflegt. Der lutherische Glaube prägte Kultur, Politik und Gesellschaft bis in die Neuzeit.",
            "duration_s": 14.0,
        },
    ],
    "sources": [
        "Hannoverische Kirchengeschichte, Landeskirche Hannovers",
        "Hinrichs, Die Reformation in Norddeutschland (2017)",
    ],
    **scene_colors(5),
}

# ─────────────────────────────────────────────────────────────────────────────
# SCENE 6: Der Dreißigjährige Krieg — Besatzung und Leid (1618-1648)
# ─────────────────────────────────────────────────────────────────────────────
scene_6 = {
    "scene_num": 6,
    "title": "Der Dreißigjährige Krieg",
    "subtitle": "Besatzung und Leid",
    "era": "1618–1648",
    "segments": [
        {
            "text": "Der Dreißigjährige Krieg, eines der verheerendsten Konflikte der europäischen Geschichte, erreichte Hannover früh. Die strategisch wichtige Stadt an der Leine war für alle kriegführenden Parteien von Interesse. Keine der Fraktionen konnte die Neutralität der Stadt garantieren.",
            "duration_s": 16.0,
        },
        {
            "text": "Kaiserliche Truppen unter dem Feldherrn Tilly besetzten die Stadt. Die Besatzung brachte Einquartierungen, Kontributionen und Plünderungen mit sich. Die Bürger Hannovers litten unter der Last, fremde Truppen versorgen zu müssen. Die Stadtkassen wurden geleert.",
            "duration_s": 16.0,
        },
        {
            "text": "Dänische und schwedische Truppen folgten den kaiserlichen Besatzern. Jeder Machtwechsel bedeutete neue Tribute und neue Drangsalierungen für die Zivilbevölkerung. Die Festungsanlagen der Stadt wurden ausgebaut, um den Belagerungen standzuhalten.",
            "duration_s": 15.0,
        },
        {
            "text": "Die Pest begleitete den Krieg. Hungersnöte und Seuchen dezimierten die Bevölkerung. Von etwa zehntausend Einwohnern vor dem Krieg schrumpfte die Zahl auf unter sechstausend. Ganze Straßenzüge standen leer. Die demographische und wirtschaftliche Erholung sollte Jahrzehnte dauern.",
            "duration_s": 16.0,
        },
        {
            "text": "Hannover diente als Versorgungslager für durchziehende Heere. Magazine und Lagerhäuser füllten sich und leerten sich mit den wechselnden Fronten. Die städtische Wirtschaft lag am Boden. Handel und Handwerk kamen nahezu zum Erliegen.",
            "duration_s": 15.0,
        },
        {
            "text": "Der Westfälische Frieden von achtundvierzig beendete das Blutvergießen. Hannover gehörte nicht zu den Verhandlungsorten, profitierte aber vom allgemeinen Friedensschluss. Der Wiederaufbau begann zögerlich. Die Stadt musste sich von ihren Wunden erholen und an eine neue politische Realität anpassen.",
            "duration_s": 16.0,
        },
        {
            "text": "Die Erinnerung an den Dreißigjährigen Krieg prägte die städtische Kultur für Generationen. Das Bewusstsein der Verwundbarkeit trieb die Stadtväter zu neuen Befestigungsanlagen und diplomatischen Bündnissen. Hannover lernte, dass Sicherheit keine Selbstverständlichkeit war.",
            "duration_s": 15.0,
        },
    ],
    "sources": [
        "Parker, Der Dreißigjährige Krieg (2018)",
        "Stadtarchiv Hannover, Kriegsakten 1618-1648",
    ],
    **scene_colors(6),
}

# ─────────────────────────────────────────────────────────────────────────────
# SCENE 7: Wiederaufbau und der Weg zur Macht (1648-1680)
# ─────────────────────────────────────────────────────────────────────────────
scene_7 = {
    "scene_num": 7,
    "title": "Wiederaufbau",
    "subtitle": "und der Weg zur Macht",
    "era": "1648–1680",
    "segments": [
        {
            "text": "Nach dem Westfälischen Frieden stand Hannover vor der gewaltigen Aufgabe des Wiederaufbaus. Zerstörte Häuser mussten erneuert, die Wirtschaft wieder belebt werden. Herzog Georg Wilhelm regierte das Fürstentum Calenberg mit Sitz in Hannover und trieb den Aufbau voran.",
            "duration_s": 16.0,
        },
        {
            "text": "Herzog Ernst August übernahm die Regierung und brachte neue Ambitionen. Er ließ die Befestigungsanlagen nach neuesten militärischen Erkenntnissen umbauen, im Stil von Vauban. Hannover wurde zur modernen Festungsstadt. Die Bastionen und Gräben prägten das Stadtbild.",
            "duration_s": 16.0,
        },
        {
            "text": "Die Wirtschaft erholte sich allmählich. Handelsgilden gewannen an Stärke. Die Textilproduktion, das Brauwesen und der Handel über die Leine bildeten das wirtschaftliche Rückgrat. DerFluss als Handelsader wurde instand gesetzt und ausgebaut.",
            "duration_s": 15.0,
        },
        {
            "text": "Ernste wissenschaftliche und kulturelle Entwicklungen deuteten sich an. Die ersten Anfänge einer aufklärerischen Denkweise erreichten die Stadt. Die höfische Kultur begann sich zu entfalten. Hannover sollte bald eine Rolle in der europäischen Geistesgeschichte spielen.",
            "duration_s": 15.0,
        },
        {
            "text": "Die Bevölkerung wuchs durch Zuwanderung aus den umliegenden Dörfern und kriegszerstörten Gebieten. Neue Handwerker und Kaufleute brachten frische Energie. Die Stadt nahm einen neuen, dynamischen Charakter an. Das Fundament für das barocke Hannover des folgenden Jahrhunderts war bereitet.",
            "duration_s": 16.0,
        },
    ],
    "sources": [
        "Dunken, Geschichte der Stadt Hannover (1992)",
        "Stadtarchiv Hannover, Wiederaufbauakten",
    ],
    **scene_colors(7),
}

# ─────────────────────────────────────────────────────────────────────────────
# SCENE 8: Ernst August und die Personalunion — Barockes Hannover (1680-1714)
# ─────────────────────────────────────────────────────────────────────────────
scene_8 = {
    "scene_num": 8,
    "title": "Barockes Hannover",
    "subtitle": "Ernst August und die Personalunion",
    "era": "1680–1714",
    "segments": [
        {
            "text": "Herzog Ernst August war eine der faszinierendsten Figuren der welfischen Geschichte. Ambitioniert, intelligent und unersättlich im Streben nach Macht, transformierte er Hannover von einer Provinzstadt zur Residenz eines Kurfürstentums. Seine Herrschaft war eine Zeit des monumentalen Wandels.",
            "duration_s": 17.0,
        },
        {
            "text": "Ernst August änderte die Erbfolgegesetze und führte das Erstgeburtsrecht ein. Diese scheinbar technische Änderung hatte weitreichende Folgen, denn sie konzentrierte die welfische Macht in einer Hand und ermöglichte später die Personalunion mit Großbritannien.",
            "duration_s": 15.0,
        },
        {
            "text": "Ein Bauboom erfasste die Stadt. Die Herrenhäuser Gärten, der Große Garten, entstanden als barocke Meisterleistung. Schloss Herrenhausen wurde zur prachtvollen Sommerresidenz. Die Alleen und Parkanlagen folgten dem Vorbild von Versailles und zeugten vom höfischen Prunk.",
            "duration_s": 16.0,
        },
        {
            "text": "Im Jahr neunundneunzighundertzweiundneunzig erhob Kaiser Leopold der Erste Ernst August zum Kurfürsten. Hannover wurde zum Kurfürstentum, eine der höchsten Ehren im Heiligen Römischen Reich. Die Stadt feierte den Aufstieg mit großen Festlichkeiten.",
            "duration_s": 16.0,
        },
        {
            "text": "Sophie von der Pfalz, die Kurfürstin, war eine der klügsten Frauen ihrer Zeit. Sie führte einen der berühmtesten intellektuellen Salons Europas. Ihr Anspruch auf den britischen Thron, abgestützt auf den Act of Settlement, sollte die Geschichte beider Nationen verändern.",
            "duration_s": 16.0,
        },
        {
            "text": "Gottfried Wilhelm Leibniz, einer der größten Philosophen und Mathematiker der Geschichte, lebte und arbeitete in Hannover. Als Hofbibliothekar schrieb er hier wichtige Werke, entwickelte die Infinitesimalrechnung und korrespondierte mit Gelehrten in ganz Europa.",
            "duration_s": 15.0,
        },
        {
            "text": "Die wissenschaftliche und philosophische Kultur am hannoverschen Hof war ein Leuchtfeuer der Aufklärung. Leibniz und seine Zeitgenossen machten Hannover zu einem Zentrum des europäischen Geisteslebens. Die Stadt profitierte von dieser intellektuellen Blüte.",
            "duration_s": 15.0,
        },
    ],
    "sources": [
        "Auerbach, Leibniz und Hannover (2011)",
        "Krampe, Kurfürstin Sophie von Hannover (2010)",
    ],
    **scene_colors(8),
}

# ─────────────────────────────────────────────────────────────────────────────
# SCENE 9: Georg Ludwig wird König Georg I. (1714-1727)
# ─────────────────────────────────────────────────────────────────────────────
scene_9 = {
    "scene_num": 9,
    "title": "König Georg I.",
    "subtitle": "Von Hannover nach London",
    "era": "1714–1727",
    "segments": [
        {
            "text": "Der Act of Settlement von neunzehnhunderteins legte die rechtliche Grundlage für eine der bemerkenswertesten dynastischen Verbindungen der europäischen Geschichte. Nach dem Tod Königin Annas von Großbritannien ging die Krone an den hannoverschen Kurfürsten Georg Ludwig.",
            "duration_s": 17.0,
        },
        {
            "text": "Georg Ludwig reiste nach London und wurde als Georg der Erste König von Großbritannien und Irland. Die Personalunion zwischen Hannover und Großbritannien war geboren. Ein deutscher Fürst saß auf dem englischen Thron. Diese Konstellation sollte einhundertdreiundzwanzig Jahre währen.",
            "duration_s": 17.0,
        },
        {
            "text": "Die Personalunion funktionierte durch Doppelregierung. Georg regierte Großbritannien persönlich, während er hannoversche Minister mit der Verwaltung des Kurfürstentums betraute. Der König besuchte Hannover nur selten, doch die Verbindung blieb eng.",
            "duration_s": 16.0,
        },
        {
            "text": "Für Hannover bedeutete die Personalunion britische Investitionen und architektonische Förderung. Das Leineschloss wurde erweitert. Englische Architektur beeinflusste das Stadtbild. Die Regierung in London nahm hannoversche Interessen in die europäische Politik auf.",
            "duration_s": 15.0,
        },
        {
            "text": "Die Guelph succession war gesichert. Georgs Sohn sollte ihm auf beiden Thronen folgen. Die dynastische Verbindung veränderte das Selbstverständnis Hannovers grundlegend. Die Stadt war nicht mehr nur Residenz eines deutschen Kurfürsten, sondern Hauptstadt eines Königreichs in Personalunion.",
            "duration_s": 16.0,
        },
        {
            "text": "Kultureller Austausch zwischen den Höfen bereicherte beide Seiten. Englische Literatur und Philosophie erreichten Hannover, während deutsche Kultur nach England strömte. Die Personalunion schuf eine einzigartige britisch-deutsche Verbindung, die bis heute spürbar ist.",
            "duration_s": 15.0,
        },
    ],
    "sources": [
        "Hatton, George I (1978)",
        "Redwood, Die hannoversche Dynastie (2015)",
    ],
    **scene_colors(9),
}

# ─────────────────────────────────────────────────────────────────────────────
# SCENE 10: Hannover als europäische Residenz (1727-1760)
# ─────────────────────────────────────────────────────────────────────────────
scene_10 = {
    "scene_num": 10,
    "title": "Hannover als Residenz",
    "subtitle": "Georg II und die europäische Diplomatie",
    "era": "1727–1760",
    "segments": [
        {
            "text": "Georg der Zweite besuchte Hannover häufiger als sein Vater. Unter seiner Herrschaft blühte die Residenzstadt auf. Das Leineschloss war ein lebendiges Zentrum höfischen Lebens, von dem aus die Geschäfte des Kurfürstentums gelenkt wurden.",
            "duration_s": 15.0,
        },
        {
            "text": "Im Jahr siebzehnhundertsiebenunddreißig wurde die Universität Göttingen gegründet. Dies war ein Meilenstein für die Aufklärung in Deutschland. Die Universität sollte bald als eine der führenden Bildungsinstitutionen Europas gelten und berühmte Gelehrte anziehen.",
            "duration_s": 17.0,
        },
        {
            "text": "Am Leineschloss florieren Oper, Theater und Ballett. Der hannoversche Hof war ein Zentrum der barocken Musikkultur. Komponisten und Musiker aus ganz Europa gastierten in Hannover. Die höfische Gesellschaft pflegte einen luxuriösen Lebensstil.",
            "duration_s": 15.0,
        },
        {
            "text": "Architektonisch wandelte sich das Stadtbild. Barocke Stadthäuser entstanden entlang der Hauptstraßen. Kirchen wurden im barocken Stil umgebaut oder erneuert. Die Stadt nahm das Gepräge einer europäischen Residenz an, vergleichbar mit Berlin oder Dresden.",
            "duration_s": 16.0,
        },
        {
            "text": "Hannover spielte eine aktive Rolle in der europäischen Diplomatie. Das Kurfürstentum vertrat seine Interessen im Reichstag und in internationalen Verhandlungen. Die Verbundenheit mit Großbritannien verlieh Hannover ein ungewöhnliches diplomatisches Gewicht.",
            "duration_s": 15.0,
        },
        {
            "text": "Der Siebenjährige Krieg brachte schwere Zeiten. Frankreich besetzte Hannover im Jahr sechzehnhundertsiebenundfünfzig. Der Herzog von Cumberland wurde bei Hastenbeck geschlagen. Die Stadt litt unter der Besatzung, doch widerstand sie tapfer. Der Krieg endete mit der Wiederherstellung der welfischen Herrschaft.",
            "duration_s": 17.0,
        },
    ],
    "sources": [
        "Aretin, Das Alte Reich (1997)",
        "Murray, Die Universität Göttingen (2005)",
    ],
    **scene_colors(10),
}

# ─────────────────────────────────────────────────────────────────────────────
# SCENE 11: Die Universität Göttingen und die Aufklärung (1737-1800)
# ─────────────────────────────────────────────────────────────────────────────
scene_11 = {
    "scene_num": 11,
    "title": "Die Universität Göttingen",
    "subtitle": "Zentrum der Aufklärung",
    "era": "1737–1800",
    "segments": [
        {
            "text": "Die Georgia Augusta, wie die Universität Göttingen offiziell hieß, war eine Gründung von europäischer Bedeutung. Herzog Georg August von Braunschweig-Lüneburg stiftete sie als Universität nach dem Vorbild von Halle und Oxford. Freiheit von Forschung und Lehre waren ihre Grundsätze.",
            "duration_s": 17.0,
        },
        {
            "text": "Berühmte Gelehrte lehrten und forschten in Göttingen. Carl Friedrich Gauß, der Fürst der Mathematiker, wirkte hier. Albrecht von Haller revolutionierte die Medizin. Georg Christoph Lichtenberg hinterließ scharfsinnige Aphorismen und experimentelle Forschungen.",
            "duration_s": 16.0,
        },
        {
            "text": "Der Göttinger Hain, eine Gruppe junger Dichter, machte die Universität zu einem Zentrum der Empfindsamkeit und des Sturm und Drang. Johann Heinrich Voß und Ludwig Hölty gehörten zu diesem Kreis. Ihre Gedichte fanden weite Verbreitung im deutschsprachigen Raum.",
            "duration_s": 16.0,
        },
        {
            "text": "Die Königliche Gesellschaft der Wissenschaften zu Göttingen wurde als eine der ersten Akademien ihrer Art gegründet. Sie förderte die Erforschung der Natur, der Geschichte und der Sprachen. Wissenschaftliche Entdeckungen aus Göttingen fanden internationale Anerkennung.",
            "duration_s": 16.0,
        },
        {
            "text": "Die Göttinger Bibliothek war eine der größten und modernsten Europas. Sie war offen für Gelehrte aller Nationen. Ihr Bestand wuchs stetig und umfasste Werke aus allen Wissensgebieten. Die Bibliothek war das intellektuelle Herz der Universität.",
            "duration_s": 15.0,
        },
        {
            "text": "Die Verbindung zwischen der Universität Göttingen und Hannover war eng. Gelehrte reisten zwischen den beiden Städten. Die aufklärerischen Ideen der Universität beeinflussten das städtische Leben in Hannover. Die Residenzstadt profitierte vom intellektuellen Glanz ihrer Universität.",
            "duration_s": 16.0,
        },
    ],
    "sources": [
        "Hammerstein, Aufklärung und Universität (2012)",
        "Fuchs, Die Göttinger Akademie der Wissenschaften (2006)",
    ],
    **scene_colors(9),
}

# ─────────────────────────────────────────────────────────────────────────────
# SCENE 12: Die Französische Revolution und das napoleonische Zeitalter (1789-1813)
# ─────────────────────────────────────────────────────────────────────────────
scene_12 = {
    "scene_num": 12,
    "title": "Das napoleonische Zeitalter",
    "subtitle": "Revolution, Besatzung, Befreiung",
    "era": "1789–1813",
    "segments": [
        {
            "text": "Die Französische Revolution von neunzehnhundertsiebenundachtzig erschütterte auch Hannover. Die Ideen von Freiheit, Gleichheit und Brüderlichkeit fanden Anhänger in der Stadt, doch das Kurfürstentum blieb monarchisch. Hannover beteiligte sich an der ersten Koalition gegen das revolutionäre Frankreich.",
            "duration_s": 17.0,
        },
        {
            "text": "Napoleon Bonaparte veränderte die politische Landkarte Europas grundlegend. Hannover wurde von französischen Truppen besetzt. Das Kurfürstentum hörte auf zu existieren. Die Welfen flohen ins Exil nach London. Die Stadt stand unter fremder Herrschaft.",
            "duration_s": 16.0,
        },
        {
            "text": "Teile des hannoverschen Gebiets wurden dem Königreich Westfalen eingegliedert, das Napoleons Bruder Jérôme Bonaparte regierte. Die Kontinentalsperre, Napoleons Wirtschaftsblockade gegen Großbritannien, verheerte den hannoverschen Handel. Die Stadt verarmte.",
            "duration_s": 17.0,
        },
        {
            "text": "Unter der französischen Herrschaft gab es sowohl Widerstand als auch Anpassung. Einige hannoversche Beamte arbeiteten mit den Besatzern zusammen, während andere in den Widerstand gingen. Die Leiden der Zivilbevölkerung waren erheblich. Steuern, Requisitionen und Zwangsrekrutierungen belasteten die Bürger.",
            "duration_s": 17.0,
        },
        {
            "text": "Die Befreiungskriege brachten die Wende. In der Völkerschlacht bei Leipzig im Oktober tausenddreihundertdreizehn besiegten die verbündeten Armeen Napoleons Streitkräfte. Die französischen Besatzer zogen sich aus Norddeutschland zurück. Hannover wurde befreit.",
            "duration_s": 16.0,
        },
        {
            "text": "Die Rückkehr der Welfen wurde in Hannover mit Jubel gefeiert. Die Dynastie, die die Stadt so lange geprägt hatte, kehrte aus dem Exil zurück. Hannover stand vor dem Beginn einer neuen Epoche, die es vom Kurfürstentum zum Königreich erheben sollte.",
            "duration_s": 15.0,
        },
    ],
    "sources": [
        "Mikaberidze, Napoleon's Wars (2020)",
        "Stadtarchiv Hannover, Besatzungsakten 1803-1813",
    ],
    **scene_colors(10),
}

# ─────────────────────────────────────────────────────────────────────────────
# SCENE 13: Das Königreich Hannover — Wiener Kongress (1814-1830)
# ─────────────────────────────────────────────────────────────────────────────
scene_13 = {
    "scene_num": 13,
    "title": "Das Königreich Hannover",
    "subtitle": "Der Wiener Kongress und die Neugestaltung",
    "era": "1814–1830",
    "segments": [
        {
            "text": "Der Wiener Kongress von tausendachthundertvierzehn bis fünfzehn ordnete Europa nach dem Sturz Napoleons neu. Für Hannover bedeutete dies eine bedeutsame Erhebung: aus dem Kurfürstentum wurde das Königreich Hannover. Georg der Dritte, zugleich König von Großbritannien, wurde erster König von Hannover.",
            "duration_s": 17.0,
        },
        {
            "text": "Die Verfassung von tausendachthundertneunzehn war für ihre Zeit bemerkenswert progressiv. Sie garantierte Grundrechte, etablierte einen Landtag und schuf eine unabhängige Justiz. Hannover war eines der ersten deutschen Staaten mit einer modernen Verfassung.",
            "duration_s": 16.0,
        },
        {
            "text": "Administrative Reformen modernisierten die Staatsverwaltung. Neue Provinzen wurden eingegliedert und in das Königreich integriert. Das Territorium Hannovers vergrößerte sich erheblich. Die Hauptstadt wandelte sich unter dem Einfluss der neoklassizistischen Architektur.",
            "duration_s": 16.0,
        },
        {
            "text": "Die Personalunion mit Großbritannien brachte Kapitalflüsse nach Hannover. Britische Investoren finanzierten den Bau von Straßen, Kanälen und Eisenbahnlinien. Die Industrialisierung begann, wenn auch langsam. Banken und Versicherungen wurden gegründet.",
            "duration_s": 15.0,
        },
        {
            "text": "Militärische Reformen schufen eine moderne hannoversche Armee. Die Truppen des Königs waren an der Seite der Briten in verschiedenen europäischen Konflikten im Einsatz. Das Militär prägte das Alltagsleben und bot vielen jungen Männern eine Karrierechance.",
            "duration_s": 15.0,
        },
        {
            "text": "Das kulturelle Leben bereicherte sich durch Theater, Musik und Verlage. Die Residenzstadt zog Künstler und Intellektuelle an. Hannover entwickelte sich zu einem der kulturellen Zentren Norddeutschlands, wenn auch im Schatten von Berlin und Wien.",
            "duration_s": 15.0,
        },
    ],
    "sources": [
        "Klein, Der Wiener Kongress (2014)",
        "Hannover, Königreich, Staatsarchiv",
    ],
    **scene_colors(11),
}

# ─────────────────────────────────────────────────────────────────────────────
# SCENE 14: Wilhelm IV und das Ende der Personalunion (1830-1837)
# ─────────────────────────────────────────────────────────────────────────────
scene_14 = {
    "scene_num": 14,
    "title": "Ende der Personalunion",
    "subtitle": "Wilhelm IV und die Trennung",
    "era": "1830–1837",
    "segments": [
        {
            "text": "Wilhelm der Vierte erbte beide Throne, den britischen und den hannoverschen. Doch unter seiner Herrschaft wuchsen die kulturellen und politischen Differenzen zwischen den beiden Ländern. Hannover blieb ein konservatives Königreich, während Großbritannien sich liberalisierte.",
            "duration_s": 16.0,
        },
        {
            "text": "Das salische Gesetz bestimmte die Erbfolge in Hannover. Nach salischem Recht konnte eine Frau nicht die Krone erben. Als Wilhelm der Vierte starb, wurde seine Nichte Victoria Königin von Großbritannien. In Hannover jedoch ging die Krone an Ernst August, den Bruder Wilhelms.",
            "duration_s": 17.0,
        },
        {
            "text": "Das Jahr achtzehnhundertsiebenunddreißig markierte das Ende der Personalunion nach einhundertdreiundzwanzig Jahren. Hannover und Großbritannien trennten sich dynastisch. Die gemeinsame Geschichte zweier Königreiche an einem Thron war beendet.",
            "duration_s": 16.0,
        },
        {
            "text": "Die Trennung hatte weitreichende wirtschaftliche Folgen. Britische Investitionen flossen nicht mehr in gleicher Weise nach Hannover. Die Stadt verlor ihren privilegierten Zugang zum britischen Markt. Die wirtschaftliche Konkurrenz mit anderen deutschen Staaten verschärfte sich.",
            "duration_s": 16.0,
        },
        {
            "text": "Politisch und kulturell divergierten die beiden Länder. Großbritannien schritt weiter in Richtung parlamentarischer Demokratie. Hannover hingegen kehrte unter Ernst August zu einer reaktionäreren Regierungsweise zurück. Die liberale Verfassung von neunzehn stand zur Disposition.",
            "duration_s": 16.0,
        },
    ],
    "sources": [
        "Müller, Das Ende der Personalunion (2013)",
        "British-Hanoverian Association Archives",
    ],
    **scene_colors(11),
}

# ─────────────────────────────────────────────────────────────────────────────
# SCENE 15: König Ernst August — Reaktion und Revolution (1837-1851)
# ─────────────────────────────────────────────────────────────────────────────
scene_15 = {
    "scene_num": 15,
    "title": "Ernst August",
    "subtitle": "Reaktion und Revolution",
    "era": "1837–1851",
    "segments": [
        {
            "text": "Ernst August bestieg den hannoverschen Thron als einer der umstrittensten Herrscher der neueren Geschichte. Seine erste Amtshandlung war die Aufhebung der liberalen Verfassung von tausendachthundertneunzehn. Dieser Schritt löste einen Sturm der Entrüstung aus.",
            "duration_s": 16.0,
        },
        {
            "text": "Die Göttinger Sieben, sieben Professoren der Universität Göttingen, protestierten öffentlich gegen die Aufhebung der Verfassung. Unter ihnen waren die Brüder Grimm, die berühmten Märchensammler und Sprachforscher. Ernst August entließ sie alle aus ihren Ämtern.",
            "duration_s": 17.0,
        },
        {
            "text": "Die Entlassung der Göttinger Sieben wurde zu einem internationalen Skandal. Zeitungen in ganz Europa berichteten über den Vorfall. Die Göttinger Sieben wurden zu Symbolen des akademischen Widerstands. Drei der Professoren verließen das Land und fanden Zuflucht im Ausland.",
            "duration_s": 16.0,
        },
        {
            "text": "Die Revolution von achtzehnhundertachtundvierzig erreichte auch Hannover. Barrikaden wurden errichtet, Demonstrationen forderten Reformen. Die Bürger forderten die Wiedereinführung der Verfassung und die Einberufung eines Parlaments. Ernst August sah sich gezwungen, Zugeständnisse zu machen.",
            "duration_s": 17.0,
        },
        {
            "text": "Eine neue Verfassung wurde ausgearbeitet. Sie war ein Kompromiss zwischen den liberalen Forderungen der Bürger und den konservativen Vorstellungen des Königs. Die politischen Lager, Liberale, Konservative und Demokraten, rangen um die Zukunft des Landes.",
            "duration_s": 16.0,
        },
        {
            "text": "Im breiteren europäischen Kontext war die Revolution von vierundachtzig ein gescheitertes Aufbegehren gegen die etablierte Ordnung. In Hannover kehrte nach einer kurzen Phase der Liberalisierung die konservative Restauration zurück. Die Grundrechte blieben auf dem Papier, wurden aber in der Praxis eingeschränkt.",
            "duration_s": 17.0,
        },
    ],
    "sources": [
        "Schröder, Die Göttinger Sieben (2012)",
        "Siemann, Die deutsche Revolution von 1848/49 (2018)",
    ],
    **scene_colors(10),
}

# ─────────────────────────────────────────────────────────────────────────────
# SCENE 16: Georg V und die preußische Annexion (1851-1866)
# ─────────────────────────────────────────────────────────────────────────────
scene_16 = {
    "scene_num": 16,
    "title": "Preußische Annexion",
    "subtitle": "Georg V und das Ende des Königreichs",
    "era": "1851–1866",
    "segments": [
        {
            "text": "Georg der Fünfte, der blinde König, regierte Hannover von achtzehnhunderteinundfünfzig bis sechzehnhundertsechsundsechzig. Trotz seiner Blindheit war er ein energischer Herrscher, der die Unabhängigkeit seines Königreichs zu verteidigen suchte. Sein Charakter wurde als stur und eigensinnig beschrieben.",
            "duration_s": 17.0,
        },
        {
            "text": "Im Konflikt zwischen Preußen und Österreich um die Vorherrschaft in Deutschland versuchte Hannover, neutral zu bleiben. Doch in der Entscheidungsschlacht des Deutschen Bundeskrieges von sechzehnhundertsechsundsechzig schlug sich Hannover auf die Seite Österreichs.",
            "duration_s": 17.0,
        },
        {
            "text": "In der Schlacht bei Langensalza erzielte die hannoversche Armee einen taktischen Sieg über die preußischen Truppen. Doch dieser Erfolg war nur von kurzer Dauer. Preußische Verstärkungen näherten sich, und Hannover musste kapitulieren. Die preußische Besatzung folgte.",
            "duration_s": 17.0,
        },
        {
            "text": "Preußen annektierte Hannover. Das Königreich hörte auf zu existieren. Die Welfen-Dynastie ging ins Exil. Der Welfenfonds, das beschlagnahmte Vermögen der königlichen Familie, wurde von Preußen verwaltet. Eine Epoche war unwiderruflich zu Ende.",
            "duration_s": 16.0,
        },
        {
            "text": "Die öffentliche Reaktion in Hannover war gespalten. Viele beweinten den Verlust der Unabhängigkeit. Monarchistische Widerstandsbewegungen entstanden, und die Welfenlegende, der Glaube an die Rückkehr des Königs, lebte in Teilen der Bevölkerung weiter.",
            "duration_s": 16.0,
        },
        {
            "text": "Die Annexion war ein Wendepunkt in der Geschichte Hannovers. Die Stadt verlor ihre Funktion als Hauptstadt und Residenz. Preußische Beamte übernahmen die Verwaltung. Hannover wurde zur Hauptstadt der preußischen Provinz Hannover. Die Identität der Stadt musste sich neu definieren.",
            "duration_s": 17.0,
        },
    ],
    "sources": [
        "Hirschfeld, Der preußische Annexionismus (2011)",
        "Mommsen, Das Ringen um den Nationalstaat (1993)",
    ],
    **scene_colors(12),
}

# ─────────────────────────────────────────────────────────────────────────────
# SCENE 17: Preußische Provinz — Hannover im Kaiserreich (1866-1890)
# ─────────────────────────────────────────────────────────────────────────────
scene_17 = {
    "scene_num": 17,
    "title": "Preußische Provinz",
    "subtitle": "Hannover im Kaiserreich",
    "era": "1866–1890",
    "segments": [
        {
            "text": "Als preußische Provinz musste sich Hannover neu erfinden. Die Integration in den preußischen Staat verlief nicht reibungslos. Viele Hannoveraner lehnten die preußische Herrschaft ab und betonten ihre welfische Identität. Der hannoversche Stolz ließ sich nicht durch einen Erlass tilgen.",
            "duration_s": 17.0,
        },
        {
            "text": "Die wirtschaftliche Transformation war dramatisch. Die Eisenbahn machte Hannover zu einem der wichtigsten Verkehrsknotenpunkte Norddeutschlands. Das Hauptbahnhofgebäude, ein architektonisches Wahrzeichen, wurde zum Symbol des modernen Hannover.",
            "duration_s": 16.0,
        },
        {
            "text": "Die Industrialisierung erfasste die Stadt mit voller Kraft. Im Jahr tausendachthunderteinundsiebzig wurde die Continental Gummiwerke gegründet, die später zu einem globalen Player in der Reifenindustrie werden sollte. Stahl, Maschinenbau und Textilien folgten als wichtige Industrien.",
            "duration_s": 16.0,
        },
        {
            "text": "Die Bevölkerung explodierte. Aus einer Provinzstadt wurde eine große Industriestadt. Neue Quartiere entstanden, um die wachsende Zahl von Arbeitern und ihren Familien unterzubringen. Die städtische Infrastruktur, Wasser, Gas, Abwasser, wurde ausgebaut.",
            "duration_s": 15.0,
        },
        {
            "text": "Die Herrenhäuser Allee, eine breite Prachtstraße, verband die Stadt mit den Schlossgärten. Parks und Grünanlagen wurden angelegt. Das Eilenriede, der riesige Stadtwald, blieb als Erholungsgebiet erhalten und wurde zum grünen Herz der Stadt.",
            "duration_s": 16.0,
        },
        {
            "text": "Das kulturelle Leben blieb lebendig. Theater, Konzerte und Ausstellungen fanden statt. Die hannoversche Identität bewahrte sich trotz preußischer Herrschaft eine gewisse Eigenständigkeit. Die Erinnerung an die königliche Zeit war in Denkmälern und Traditionen gegenwärtig.",
            "duration_s": 16.0,
        },
    ],
    "sources": [
        "Hein, Die preußische Provinz Hannover (2016)",
        "Continental AG, Firmenchronik",
    ],
    **scene_colors(13),
}

# ─────────────────────────────────────────────────────────────────────────────
# SCENE 18: Industrie, Wissenschaft und das wilhelminische Hannover (1890-1914)
# ─────────────────────────────────────────────────────────────────────────────
scene_18 = {
    "scene_num": 18,
    "title": "Wilhelminisches Hannover",
    "subtitle": "Industrie, Wissenschaft, Fortschritt",
    "era": "1890–1914",
    "segments": [
        {
            "text": "Continental Gummiwerke wuchs zu einem globalen Industriegiganten heran. Von Hannover aus belieferte das Unternehmen Märkte in ganz Europa und Übersee. Die Gummiindustrie schuf tausende Arbeitsplätze und zog Arbeiter aus den umliegenden Regionen an.",
            "duration_s": 16.0,
        },
        {
            "text": "Arbeiterbewegungen und frühe sozialistische Organisationen entstanden. Die Industriearbeiterschicht formierte sich und forderte bessere Arbeitsbedingungen, kürzere Arbeitszeiten und politische Mitbestimmung. Die SPD wurde in Hannover zu einer starken politischen Kraft.",
            "duration_s": 16.0,
        },
        {
            "text": "Die Ursprünge der Hannover Messe, des wichtigsten Industriemesses der Welt, reichen in diese Zeit zurück. Erste Industrieausstellungen präsentierten die neuesten Erzeugnisse hannoverscher Fabriken. Die Messe sollte Hannovers Ruf als Industriestadt für das zwanzigste Jahrhundert begründen.",
            "duration_s": 17.0,
        },
        {
            "text": "Wissenschaftliche Institutionen erweiterten sich. Die Technische Hochschule Hannover, heute Leibniz Universität, bildete Ingenieure und Naturwissenschaftler aus. Die Stadt wurde zu einem Zentrum der technischen Forschung und Entwicklung.",
            "duration_s": 15.0,
        },
        {
            "text": "Der Zoo Hannover, im Jahr tausendachthundertsiebenundsiebzig gegründet, wurde zu einem beliebten Ausflugsziel. Architektonisch prägten Gründerzeit und Jugendstil das Stadtbild. Prachtvolle Wohnhäuser und Geschäftshäuser entstanden in den neuen Stadtvierteln.",
            "duration_s": 16.0,
        },
        {
            "text": "Die sozialen Bedingungen der Arbeiter waren hart. Enge Wohnquartiere, lange Arbeitszeiten und geringe Löhne kennzeichneten den Alltag vieler. Öffentliche Gesundheitsfürsorge und Bildungseinrichtungen wurden langsam ausgebaut, reichten aber nicht aus, um die sozialen Probleme zu lösen.",
            "duration_s": 16.0,
        },
    ],
    "sources": [
        "Hannover Messe, Archiv und Historie",
        "Tießler, Arbeiterbewegung in Hannover (2014)",
    ],
    **scene_colors(13),
}

# ─────────────────────────────────────────────────────────────────────────────
# SCENE 19: Der Erste Weltkrieg (1914-1918)
# ─────────────────────────────────────────────────────────────────────────────
scene_19 = {
    "scene_num": 19,
    "title": "Der Erste Weltkrieg",
    "subtitle": "Hannover im Großen Krieg",
    "era": "1914–1918",
    "segments": [
        {
            "text": "Mit dem Ausbruch des Ersten Weltkriegs im August neunzehnhundertvierzehn wurde Hannover in den mörderischen Konflikt hineingezogen. Die hannoverschen Regimenter rückten an die Westfront. Tausende junge Männer aus der Stadt kämpften in den Schützengräben Frankreichs und Belgiens.",
            "duration_s": 17.0,
        },
        {
            "text": "An der Heimatfront wandelte sich die Stadt. Frauen übernahmen die Arbeit in den Fabriken, die Männer an die Front gegangen waren. Kriegsanleihen wurden verkauft, Lebensmittel rationiert. Die Industrieproduktion wurde auf Rüstungsgüter umgestellt.",
            "duration_s": 16.0,
        },
        {
            "text": "Das Hindenburg-Programm forderte maximale industrielle Produktion für den Krieg. Hannovers Fabriken stellten Munition, Ausrüstung und Waffen her. Die Continental-Werke produzierten Gummiprodukte für das Militär. Die Arbeiter arbeiteten unter immer härteren Bedingungen.",
            "duration_s": 16.0,
        },
        {
            "text": "Die britische Seeblockade schnitt Deutschland von Importen ab. Nahrungsmittel wurden knapp. Der Wintertod von tausendsechzehnhundertsiebzehn forderte viele Opfer unter der Zivilbevölkerung. Schwarzmärkte entstanden. Die Ernährungslage wurde katastrophal.",
            "duration_s": 16.0,
        },
        {
            "text": "Die Novemberrevolution von achtzehnhundertachtzehn erreichte auch Hannover. Streiks und Arbeiter- und Soldatenräte bildeten sich. Die Monarchie brach zusammen. Der Herzog von Braunschweig, ein Verwandter der Welfen, dankte ab. Die Weimarer Republik begann.",
            "duration_s": 16.0,
        },
        {
            "text": "Tausende hannoversche Soldaten kehrten nicht aus dem Krieg zurück. Die Stadt trauerte um ihre Gefallenen. Der Krieg hatte die Gesellschaft grundlegend verändert. Alte Ordnungen waren gefallen, neue politische Kräfte drängten nach vorne.",
            "duration_s": 15.0,
        },
    ],
    "sources": [
        "Strachan, Der Erste Weltkrieg (2004)",
        "Stadtarchiv Hannover, Kriegsteilnehmerakten",
    ],
    **scene_colors(14),
}

# ─────────────────────────────────────────────────────────────────────────────
# SCENE 20: Die Weimarer Republik in Hannover (1918-1933)
# ─────────────────────────────────────────────────────────────────────────────
scene_20 = {
    "scene_num": 20,
    "title": "Die Weimarer Republik",
    "subtitle": "Hannover zwischen Chaos und Kreativität",
    "era": "1918–1933",
    "segments": [
        {
            "text": "Die Weimarer Republik begann in Hannover mit politischem Chaos. Spartakusaufstände und rechtsextreme Freikorps kämpften um die Macht in der Straßenpolitik. Die Stadt war ein Schlachtfeld konkurrierender politischer Ideologien. Die junge Demokratie stand von Anfang an unter Druck.",
            "duration_s": 17.0,
        },
        {
            "text": "Hannover war eine Hochburg der SPD und der Arbeiterbewegung. Der Kapp-Putsch von neunzehnhundertzwanzig löste einen Generalstreik aus, an dem sich auch hannoversche Arbeiter massenhaft beteiligten. Die Stadt stand fest auf der Seite der Republik.",
            "duration_s": 16.0,
        },
        {
            "text": "In den goldenen zwanziger Jahren erlebte Hannover eine Blütezeit der Architektur. Moderne Siedlungen im Stil des Neuen Bauens entstanden. Der Stadtplaner Otto Haesler schuf in Alfeld, nahe Hannover, richtungsweisende Wohnbauten. Die Gartenstadtbewegung beeinflusste die Stadtplanung.",
            "duration_s": 17.0,
        },
        {
            "text": "Das kulturelle Leben florierte. Kabarett, avantgardistische Kunst und moderne Architektur prägten die Stadtkultur. Hannover wurde zu einem Zentrum der klassischen Moderne. Museen und Galerien zeigten Werke der expressionistischen und konstruktivistischen Avantgarde.",
            "duration_s": 16.0,
        },
        {
            "text": "Die Weltwirtschaftskrise traf Hannover hart. Arbeitslosigkeit grassierte, Armut verbreitete sich. Die politische Radikalisierung nahm zu. Extremistische Parteien, sowohl Kommunisten als auch Nationalsozialisten, gewannen an Anhängerschaft. Die Weimarer Koalition zerfiel.",
            "duration_s": 16.0,
        },
        {
            "text": "Bei den Wahlen von neunzehnhundertzweiunddreißig erzielte die NSDAP erhebliche Gewinne auch in Hannover. Die Weimarer Republik befand sich im Endstadium. Die Demokratie war geschwächt, und dunkle Zeiten kündigten sich an.",
            "duration_s": 15.0,
        },
    ],
    "sources": [
        "Peukert, Die Weimarer Republik (1987)",
        "Stadtarchiv Hannover, Weimarer Republik Bestand",
    ],
    **scene_colors(15),
}

# ─────────────────────────────────────────────────────────────────────────────
# SCENE 21: Die Machtergreifung — Nationalsozialismus in Hannover (1933-1938)
# ─────────────────────────────────────────────────────────────────────────────
scene_21 = {
    "scene_num": 21,
    "title": "Nationalsozialismus",
    "subtitle": "Die Machtergreifung in Hannover",
    "era": "1933–1938",
    "segments": [
        {
            "text": "Die Machtübernahme der Nationalsozialisten im Jahr neunzehnhundertdreiunddreißig veränderte Hannover grundlegend. Gleichschaltung wurde das Leitmotiv. Politische Parteien und Gewerkschaften wurden aufgelöst. Demokratische Institutionen wurden entmachtet. Die Stadt verlor ihre Freiheit.",
            "duration_s": 16.0,
        },
        {
            "text": "Die jüdische Gemeinde Hannovers hatte eine lange und reiche Geschichte. Jahrhundertelang hatten jüdische Bürger zum wirtschaftlichen und kulturellen Leben der Stadt beigetragen. Unter den Nationalsozialisten begann ihre systematische Verfolgung. Boykotte, Gesetze und Enteignungen folgten einander.",
            "duration_s": 17.0,
        },
        {
            "text": "Die Synagoge in der Calenberger Neustadt, einst das Zentrum des jüdischen Gemeindelebens, wurde während der Reichspogromnacht vom neunten zum zehnten November neunzehnhundertachtunddreißig zerstört. Jüdische Geschäfte wurden geplündert, Wohnungen verwüstet. Hannoverer Juden wurden verhaftet.",
            "duration_s": 18.0,
        },
        {
            "text": "Die Gestapo richtete sich in Hannover ein. Ihr Hauptquartier wurde zum Ort des Terrors. Verhöre, Folter und Verschleppungen waren an der Tagesordnung. Opponenten des Regimes, Gewerkschafter, Sozialdemokraten und andere, wurden verfolgt und inhaftiert.",
            "duration_s": 16.0,
        },
        {
            "text": "Große Bauvorhaben prägten die Stadt im nationalsozialistischen Stil. Der Maschsee, ein künstlicher See im Süden der Stadt, wurde zwischen neunzehnhundertdreiunddreißig und sechsunddreißig vom Reichsarbeitsdienst angelegt. Ein Stadion für die Olympia-Vorbereitungen wurde gebaut.",
            "duration_s": 17.0,
        },
        {
            "text": "Widerstand gab es, aber er war isoliert und gefährlich. Einzelne Personen und kleine Gruppen leisteten stillen oder offenen Widerstand. Sie riskierten ihr Leben. Die Geschichte des Widerstands in Hannover ist ein Kapitel, das erst in jüngerer Zeit voll gewürdigt wurde.",
            "duration_s": 16.0,
        },
    ],
    "sources": [
        "Stadtarchiv Hannover, Dokumentationszentrum NS-Zwangsarbeit",
        "Barkai, Das Judentum in Hannover (2015)",
    ],
    **scene_colors(16),
}

# ─────────────────────────────────────────────────────────────────────────────
# SCENE 22: Der Zweite Weltkrieg — Zerstörung (1939-1945)
# ─────────────────────────────────────────────────────────────────────────────
scene_22 = {
    "scene_num": 22,
    "title": "Der Zweite Weltkrieg",
    "subtitle": "Zerstörung und Leid",
    "era": "1939–1945",
    "segments": [
        {
            "text": "Im Zweiten Weltkrieg wurde Hannover zu einem wichtigen Rüstungsstandort des nationalsozialistischen Deutschlands. Die Fabriken der Stadt produzierten Waffen, Munition und Ausrüstung für die Wehrmacht. Continental stellte Gummi für Panzer und Flugzeuge her. Die Stadt wurde zum legitimen militärischen Ziel.",
            "duration_s": 18.0,
        },
        {
            "text": "Zehntausende Zwangsarbeiter wurden nach Hannover verschleppt. Sie kamen aus Polen, der Sowjetunion, Frankreich und vielen anderen Ländern. In Lagern unter unmenschlichen Bedingungen eingesperrt, mussten sie in den Fabriken arbeiten. Das Konzentrationslager Ahlem war ein Ort des Schreckens.",
            "duration_s": 17.0,
        },
        {
            "text": "Achtundachtzig alliierte Luftangriffe trafen Hannover. Bombardements zerstörten Häuser, Fabriken und Straßen. Der verheerendste Angriff am fünfundzwanzigsten und sechsundzwanzigsten März neunzehnhundertfünfundvierzig legte die Innenstadt in Schutt und Asche. Neunzig Prozent der Altstadt wurden zerstört.",
            "duration_s": 18.0,
        },
        {
            "text": "Das Leineschloss, die Marktkirche und die Kreuzkirche erlitten schwere Schäden. Die Aegidienkirche wurde zur Mahnmalruine erhalten. Kirchen, die über Jahrhunderte das Stadtbild geprägt hatten, waren nun Trümmer. Das kulturelle Erbe der Stadt war weitgehend vernichtet.",
            "duration_s": 16.0,
        },
        {
            "text": "Tausende Zivilisten starben bei den Bombardements. Noch mehr wurden obdachlos. Die Zahl der Todesopfer unter der Zivilbevölkerung ist bis heute umstritten, aber sie lag in den Tausenden. Der Alltag im Bombenkrieg wurde zu einem Überlebenskampf.",
            "duration_s": 16.0,
        },
        {
            "text": "Im April neunzehnhundertfünfundvierzig rückten alliierte Truppen vor. Amerikanische und britische Einheiten befreiten die Stadt. Die Zwangsarbeiterlager wurden aufgelöst. Die Überlebenden befreiten sich aus den Lagern. Die nationalsozialistische Herrschaft in Hannover war beendet.",
            "duration_s": 16.0,
        },
        {
            "text": "Hannover lag in Trümmern. Von einer einst blühenden Industriestadt war nur noch ein Trümmerfeld übrig. Die Stadt, die ein Jahrtausend Geschichte aufgebaut hatte, war in wenigen Jahren fast vollständig zerstört worden. Der Wiederaufbau würde Jahrzehnte dauern.",
            "duration_s": 16.0,
        },
    ],
    "sources": [
        "Friedrich, Der Brand (2002)",
        "NS-Dokumentationszentrum Hannover",
    ],
    **scene_colors(17),
}

# ─────────────────────────────────────────────────────────────────────────────
# SCENE 23: Trümmerfrauen und der Neuanfang (1945-1950)
# ─────────────────────────────────────────────────────────────────────────────
scene_23 = {
    "scene_num": 23,
    "title": "Trümmerfrauen",
    "subtitle": "und der Neuanfang",
    "era": "1945–1950",
    "segments": [
        {
            "text": "Nach dem Ende des Zweiten Weltkriegs präsentierte sich Hannover als ein Feld der Trümmer. Die britische Militärregierung übernahm die Verwaltung und richtete ihr Hauptquartier für die britische Besatzungszone in Hannover ein. Die Stadt wurde zum Verwaltungszentrum des neu entstehenden Landes Niedersachsen.",
            "duration_s": 17.0,
        },
        {
            "text": "Die Trümmerfrauen wurden zum Symbol des Wiederaufbaus. Frauen jeder Altersgruppe räumten mit bloßen Händen und einfachen Werkzeugen die Straßen und Häuser frei. Sie sortierten verwertbares Material von Schutt. Ihre Leistung war enorm und ist bis heute ein Mythos der Nachkriegszeit.",
            "duration_s": 17.0,
        },
        {
            "text": "Nahrungsmittel waren knapp. Rationierung und Schwarzmarkt bestimmten den Alltag. Die Versorgungslage verbesserte sich nur langsam. Der Winter neunzehnhundertsechsundvierzig war besonders hart. Kälte und Hunger suchten die Bevölkerung heim.",
            "duration_s": 16.0,
        },
        {
            "text": "Vertriebene und Flüchtlinge aus den ehemaligen deutschen Ostgebieten strömten nach Niedersachsen. Die Bevölkerung Hannovers explodierte. Neue Wohnquartiere mussten improvisiert werden. Die Integration der Neubürger war eine der größten Herausforderungen der Nachkriegszeit.",
            "duration_s": 16.0,
        },
        {
            "text": "Im Jahr neunzehnhundertsechsundvierzig wurde das Land Niedersachsen gegründet. Hannover wurde seine Landeshauptstadt. Hinrich Wilhelm Kopf, der erste Ministerpräsident, leitete den demokratischen Neuaufbau ein. Die Stadt hatte eine neue politische Rolle gefunden.",
            "duration_s": 16.0,
        },
        {
            "text": "Die Währungsreform von neunzehnhundertachtundvierzig läutete das Wirtschaftswunder ein. Die D-Mark ersetzte die wertlose Reichsmark. Über Nacht verbesserte sich die wirtschaftliche Lage. Das Wirtschaftswunder hatte begonnen, und Hannover sollte davon maßgeblich profitieren.",
            "duration_s": 16.0,
        },
    ],
    "sources": [
        "Höfling, Die Trümmerfrauen (2010)",
        "Landeszentrale für politische Bildung Niedersachsen",
    ],
    **scene_colors(18),
}

# ─────────────────────────────────────────────────────────────────────────────
# SCENE 24: Wiederaufbau und das moderne Hannover (1950-1970)
# ─────────────────────────────────────────────────────────────────────────────
scene_24 = {
    "scene_num": 24,
    "title": "Wiederaufbau",
    "subtitle": "Das moderne Hannover entsteht",
    "era": "1950–1970",
    "segments": [
        {
            "text": "Der Wiederaufbau Hannovers prägte das Stadtbild bis in die Gegenwart. Moderne Architektur ersetzte die zerstörte Altstadt. Dieser Prozess war nicht ohne Kontroversen. Kritiker bemängelten den Verbleib noch stehender historischer Gebäude, die dem modernen Straßenbau weichen mussten.",
            "duration_s": 17.0,
        },
        {
            "text": "Das neue Rathaus, ein Architekturdenkmal zwischen Vorfahren und Moderne, wurde zwischen neunzehnhundertsiebenunddreißig und den fünfziger Jahren erbaut. Seine Kuppel mit dem Aufzug bot einen Panoramablick über die wachsende Stadt. Das Rathaus wurde zum Symbol des neuen Hannover.",
            "duration_s": 17.0,
        },
        {
            "text": "Die Industrie erholte sich rasch. Continental, Volkswagen, das hannoversche Werk eröffnete neunzehnhundertachtundfünfzig und ist heute das wichtigste Nutzfahrzeugwerk der Marke, Sennheiser und Hanomag beschäftigten Tausende. Die Hannover Messe erlebte ihre Renaissance als internationale Leitmesse.",
            "duration_s": 17.0,
        },
        {
            "text": "Die städtische Planung wandte sich der Infrastruktur zu. Ringstraßen und Autobahnanschlüsse wurden gebaut. Die Vororte wuchsen. Die Technische Hochschule wurde zur Universität erhoben und zog Studierende aus ganz Deutschland an.",
            "duration_s": 15.0,
        },
        {
            "text": "Gastarbeiter aus der Türkei und Südeuropa kamen in den sechziger Jahren nach Hannover. Sie halfen, den Arbeitskräftemangel in den Fabriken zu beheben. Die türkische Gemeinde wuchs und bereicherte die städtische Kultur. Hannover wurde allmählich zu einer multikulturellen Stadt.",
            "duration_s": 16.0,
        },
        {
            "text": "Die Herrenhäuser Gärten wurden restauriert und zu einem der beliebtesten Ausflugsziele der Region. Der Große Garten erstrahlte in seiner alten barocken Pracht. Die Restaurierung war ein Zeichen der Rückbesinnung auf die kulturelle Identität der Stadt.",
            "duration_s": 16.0,
        },
    ],
    "sources": [
        "Stadtplanungsamt Hannover, Wiederaufbauakten",
        "Volkswagen AG, Geschichte des Hannover-Werks",
    ],
    **scene_colors(19),
}

# ─────────────────────────────────────────────────────────────────────────────
# SCENE 25: Hannovers Kulturleben im 20. Jahrhundert (1950-2000)
# ─────────────────────────────────────────────────────────────────────────────
scene_25 = {
    "scene_num": 25,
    "title": "Kulturleben",
    "subtitle": "Hannovers kulturelle Vielfalt",
    "era": "1950–2000",
    "segments": [
        {
            "text": "Die Staatsoper Hannover pflegte eine lange Tradition der Oper und des Balletts. Mit einem Repertoire von klassischen Werken bis zu zeitgenössischen Produktionen zog sie ein treues Publikum an. Die Opernhaus-Ensemble gehörte zu den renommiertesten Deutschlands.",
            "duration_s": 16.0,
        },
        {
            "text": "Das Schauspielhaus Hannover bot dramatische Aufführungen von höchster Qualität. Regisseure und Schauspieler von nationalem Ruf arbeiteten hier. Das Theater war ein Spiegel der gesellschaftlichen Diskussionen und der kulturellen Entwicklungen der Zeit.",
            "duration_s": 15.0,
        },
        {
            "text": "Die Museen Hannovers waren vielfältig. Das Niedersächsische Landesmuseum präsentierte naturkundliche und kulturhistorische Sammlungen. Die Kestnergesellschaft zeigte moderne Kunst. Das Sprengel Museum, neunzehnhundertsiebenundneunzig eröffnet, widmete sich der modernen und zeitgenössischen Kunst.",
            "duration_s": 17.0,
        },
        {
            "text": "Die NDR Radiophilharmonie machte Hannover zu einem Zentrum der klassischen Musik. Konzerte und Aufnahmen erreichten ein bundesweites Publikum. Die Musikszene reichte von Klassik über Jazz bis hin zu experimentellen Formen.",
            "duration_s": 15.0,
        },
        {
            "text": "Hannover als Medienstandort profitierte von den Studios des NDR. Fernseh- und Radioproduktionen wurden in der Stadt erstellt. Die Vorbereitungen für die Expo zweitausend intensivierten die medienbezogenen Aktivitäten und brachten internationale Aufmerksamkeit.",
            "duration_s": 15.0,
        },
        {
            "text": "Die Welfen-Dynastie, die Hannover einst regierte, lebte in der kulturellen Erinnerung weiter. Denkmäler, Straßennamen und historische Traditionen erinnerten an die königliche Vergangenheit. Das kulturelle Erbe der Welfenzeit war untrennbar mit der Identität der Stadt verbunden.",
            "duration_s": 16.0,
        },
    ],
    "sources": [
        "Sprengel Museum Hannover, Sammlung und Geschichte",
        "NDR, Standortgeschichte Hannover",
    ],
    **scene_colors(20),
}

# ─────────────────────────────────────────────────────────────────────────────
# SCENE 26: Die EXPO 2000 und die Weltbühne (1990-2005)
# ─────────────────────────────────────────────────────────────────────────────
scene_26 = {
    "scene_num": 26,
    "title": "Die EXPO 2000",
    "subtitle": "Hannover auf der Weltbühne",
    "era": "1990–2005",
    "segments": [
        {
            "text": "Die Bewerbung Hannovers für die Weltausstellung EXPO zweitausend war ein Wagnis. Gegen starke internationale Konkurrenz setzte sich die niedersächsische Landeshauptstadt durch. Die Vorbereitungszeit war geprägt von gigantischen Infrastrukturinvestitionen und öffentlichen Debatten über Kosten und Nutzen.",
            "duration_s": 17.0,
        },
        {
            "text": "Das Leitthema der EXPO war Mensch, Natur, Technik. Der Ausstellungsgelände in Hannover-Laatzzen wurde auf einem ehemaligen Messegelände errichtet. Hunderte Nationen und Organisationen präsentierten ihre Pavillons mit futuristischer Architektur und innovativen Ausstellungskonzepten.",
            "duration_s": 17.0,
        },
        {
            "text": "Die architektonischen Highlights der EXPO waren spektakulär. Das Holländische Pavillon mit seinen Bodenschichten, der japanische Pavillon aus recyceltem Papier und der christliche Pavillon waren nur einige der beeindruckenden Bauwerke. Die EXPO zog Millionen Besucher aus der ganzen Welt an.",
            "duration_s": 17.0,
        },
        {
            "text": "Die Besucherzahlen und die wirtschaftlichen Auswirkungen wurden intensiv debattiert. Die EXPO blieb hinter den Erwartungen zurück, was die Besuchszahlen anging. Dennoch hinterließ sie ein bleibendes Erbe. Das Messegelände, die Infrastruktur und die internationale Bekanntheit Hannovers profitierten von der Weltausstellung.",
            "duration_s": 17.0,
        },
        {
            "text": "Die deutsche Wiedervereinigung veränderte die geopolitische Lage Hannovers. Die Stadt war keine Grenzstadt mehr. Die Nähe zu den neuen Bundesländern eröffnete neue wirtschaftliche Möglichkeiten. Hannover rückte näher an das geografische Zentrum des wiedervereinten Deutschlands.",
            "duration_s": 16.0,
        },
    ],
    "sources": [
        "EXPO 2000 Hannover GmbH, Abschlussbericht",
        "Roth, Die EXPO 2000 im Rückblick (2010)",
    ],
    **scene_colors(21),
}

# ─────────────────────────────────────────────────────────────────────────────
# SCENE 27: Hannover heute — Technologie, Kultur und Wirtschaft (2005-present)
# ─────────────────────────────────────────────────────────────────────────────
scene_27 = {
    "scene_num": 27,
    "title": "Hannover heute",
    "subtitle": "Technologie, Kultur und Wirtschaft",
    "era": "2005–heute",
    "segments": [
        {
            "text": "Hannover im einundzwanzigsten Jahrhundert ist eine moderne Großstadt mit rund fünfhundertdreißigtausend Einwohnern. Die Stadt hat sich von der Industriestadt des zwanzigsten Jahrhunderts zu einem vielseitigen Zentrum für Technologie, Kultur und Wirtschaft entwickelt.",
            "duration_s": 16.0,
        },
        {
            "text": "Die CeBIT, einst die weltweit größte IT-Messe, machte Hannover zum Treffpunkt der globalen Technologiebranche. Auch nach dem Ende der CeBIT bleibt die Deutsche Messe AG ein zentraler Wirtschaftsfaktor. Messen wie die Hannover Messe und die Agritechnica ziehen internationale Aussteller an.",
            "duration_s": 17.0,
        },
        {
            "text": "Die Leibniz Universität Hannover ist eine der größten Universitäten Norddeutschlands. Mit rund dreißigtausend Studierenden in various Fakultäten treibt sie Forschung und Innovation voran. Die Medizinische Hochschule Hannover ist ein führendes Zentrum für medizinische Forschung und Patientenversorgung.",
            "duration_s": 17.0,
        },
        {
            "text": "Volkswagen, Continental und Sennheiser haben ihre Hauptsitze in und um Hannover. Diese Unternehmen repräsentieren die wirtschaftliche Stärke der Region. Die Region Hannover ist ein wichtiger Standort für Automobilbau, Reifentechnologie, Audiotechnik und Spitzentechnologie.",
            "duration_s": 16.0,
        },
        {
            "text": "Die Herrenhäuser Gärten, der Maschsee, die Eilenriede und die wiedererstandene Altstadt bilden die touristischen Highlights der Stadt. Die Kombination aus historischen Parks, Seenlandschaft und urbanem Grün macht Hannover zu einer besonders lebenswerten Stadt.",
            "duration_s": 16.0,
        },
        {
            "text": "Hannover steht vor den Herausforderungen des einundzwanzigsten Jahrhunderts. Infrastruktur, Wohnungsnot und Klimaanpassung erfordern politische Antworten. Die internationale Community wächst. Die Stadt sucht nach Wegen, Wachstum und Lebensqualität in Einklang zu bringen.",
            "duration_s": 16.0,
        },
    ],
    "sources": [
        "Region Hannover, Wirtschaftsbericht",
        "Deutsche Messe AG, Historie und Gegenwart",
    ],
    **scene_colors(22),
}

# ─────────────────────────────────────────────────────────────────────────────
# SCENE 28: Epilog — Eine Stadt im Wandel (present)
# ─────────────────────────────────────────────────────────────────────────────
scene_28 = {
    "scene_num": 28,
    "title": "Epilog",
    "subtitle": "Eine Stadt im Wandel",
    "era": "Gegenwart",
    "segments": [
        {
            "text": "Die Geschichte Hannovers spannt sich über mehr als eintausend Jahre. Von einer germanischen Siedlung an der Leine zur modernen Großstadt, von einer mittelalterlichen Handelsstadt zur Hauptstadt eines Königreichs, von einer zerstörten Ruine zum Symbol des Wirtschaftswunders.",
            "duration_s": 17.0,
        },
        {
            "text": "Wiederstandskraft ist das Leitmotiv dieser Stadt. Kriege, Zerstörung und Besatzung haben Hannover wieder und wieder getroffen. Jedes Mal hat die Stadt sich erholt und neu erfunden. Die Trümmerfrauen des Wiederaufbaus stehen für diesen unbeugsamen Geist.",
            "duration_s": 16.0,
        },
        {
            "text": "Handel und Innovation haben Hannover seit jeher geprägt. Von der mittelalterlichen Gilde zur globalen Messe, von der Handwerksstatt zum Hightech-Unternehmen. Die Stadt hat immer an der Spitze wirtschaftlicher und technologischer Entwicklung gestanden.",
            "duration_s": 16.0,
        },
        {
            "text": "Kulturelles Streben und der Wunsch nach Bedeutung zeichnen Hannover aus. Die Welfen-Dynastie, die Universität Göttingen, die Herrenhäuser Gärten, die EXPO — die Stadt hat immer nach kultureller und intellektueller Exzellenz gestrebt.",
            "duration_s": 15.0,
        },
        {
            "text": "Hannovers einzigartige Position ist das Ergebnis dieser tausendjährigen Entwicklung. Hauptstadt von Niedersachsen, internationale Messestadt, Universitätsstadt, Industriezentrum und grüne Stadt. Der Eilenriede, einer der größten Stadtwälder Europas, zeugt von der Verbundenheit mit der Natur.",
            "duration_s": 17.0,
        },
        {
            "text": "Dies ist die Geschichte einer Stadt, die sich nie aufgehört hat zu wandeln. Und doch bleibt sie erkennbar. Die Leine fließt noch immer durch die Stadtmitte. Die Marktkirche thront über dem Platz, wo vor achthundert Jahren die ersten Händler ihre Waren anboten. Hannover — eine Stadt im Wandel, doch stets sich selbst treu.",
            "duration_s": 18.0,
        },
    ],
    "sources": [
        "Hans-Claus Riepe, Kleine Geschichte Hannovers (2013)",
        "Stadt Hannover, Offizielle Chronik",
    ],
    **scene_colors(23),
}


def main():
    """Write all scene JSON files to scripts/scenes/ directory."""
    os.makedirs(SCENES_DIR, exist_ok=True)

    scenes = [
        scene_1, scene_2, scene_3, scene_4, scene_5, scene_6, scene_7,
        scene_8, scene_9, scene_10, scene_11, scene_12, scene_13, scene_14,
        scene_15, scene_16, scene_17, scene_18, scene_19, scene_20, scene_21,
        scene_22, scene_23, scene_24, scene_25, scene_26, scene_27, scene_28,
    ]

    total_segments = 0
    total_duration = 0.0
    total_words = 0

    for scene in scenes:
        num = scene["scene_num"]
        # Verify each segment is under 1024 chars
        for seg in scene["segments"]:
            text = seg["text"]
            if len(text) > 1024:
                print(f"WARNING: Scene {num} segment exceeds 1024 chars ({len(text)} chars)")
            total_words += len(text.split())
            total_segments += 1
            total_duration += seg["duration_s"]

        # Remove 'background' key if present (not part of schema)
        for seg in scene["segments"]:
            seg.pop("background", None)

        path = os.path.join(SCENES_DIR, f"scene_{num:02d}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(scene, f, ensure_ascii=False, indent=2)
        print(f"  Written: scene_{num:02d}.json ({len(scene['segments'])} segments)")

    print(f"\n{'='*60}")
    print(f"Total scenes:       {len(scenes)}")
    print(f"Total segments:      {total_segments}")
    print(f"Total words:         {total_words}")
    print(f"Total duration:      {total_duration:.0f}s ({total_duration/60:.1f} min)")
    print(f"Output directory:    {SCENES_DIR}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

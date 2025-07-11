import os

# Define BASE_DIR to point to the main CompanyAnalyzer/ project directory.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Folder Paths ---
# These paths are now relative to the BASE_DIR
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
REPORTS_FOLDER = os.path.join(BASE_DIR, 'reports')
TEMPLATES_FOLDER = os.path.join(BASE_DIR, 'templates')
STATIC_FOLDER = os.path.join(BASE_DIR, 'static')

# --- File Paths ---
# These paths are also relative to the BASE_DIR
SETTINGS_FILE = os.path.join(BASE_DIR, 'settings.json')
HISTORY_FILE = os.path.join(BASE_DIR, 'history.json')
PE_LIST_FILE = os.path.join(BASE_DIR, 'pe_firms.json')
NATIONS_FILE = os.path.join(BASE_DIR, 'nations.json') 
PUBLIC_MANAGERS_FILE = os.path.join(BASE_DIR, 'public_asset_managers.json')

# --- Default Values / Constants ---
# Allowed file extensions for uploads
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

# Default list of Private Equity firms (can be updated via UI)
def get_default_pe_firms():
    """Returns a default list of private equity firms."""
    return [
        "Addor Capital", "Affinity Equity Partners", "Archer Capital", "Axiom Asia",
        "BGH Capital", "Boyu Capital", "CBC Group", "Centurium Capital",
        "China Chengtong Holdings Group", "China Media Capital", "China Merchants Capital",
        "China Reform Fund Management", "CITIC Capital", "CoStone Capital", "Cowin Capital",
        "CPE", "DCP Capital", "Dymon Asia Private Equity", "Ekuinas",
        "FountainVest Partners", "Hillhouse Capital Group", "Hony Capital",
        "Hopu Investment Management", "JAFCO", "JIC Capital", "Leopard Capital LP",
        "Mekong Capital", "MBK Partners", "Northstar Group", "Oriza Holdings",
        "Pacific Equity Partners", "PAG", "Primavera Capital Group",
        "Quadria Capital", "Quadrant Private Equity", "RRJ Capital", "Seavi Advent",
        "Tiantu Capital", "Tybourne Capital Management", "Yunfeng Capital",
        "Zhongzhi Capital", "ZWC Partners",
        "3G Capital", "ABS Capital", "Adams Street Partners", "Advent International",
        "AEA Investors", "American Securities", "Angelo, Gordon & Co.",
        "Apollo Global Management", "Ares Management", "Arlington Capital Partners",
        "Auldbrass Partners", "Avenue Capital Group", "Avista Capital Partners",
        "Bain Capital", "BDT & MSD Partners", "Berkshire Partners", "Blackstone Group",
        "Blue Owl Capital", "Blum Capital", "Brentwood Associates",
        "Bruckmann, Rosser, Sherrill & Co.", "Brynwood Partners", "CapitalG",
        "Carlyle Group", "Castle Harlan", "CCMP Capital", "Centerbridge Partners",
        "Cerberus Capital Management", "Charlesbank Capital Partners",
        "Chicago Growth Partners", "CI Capital Partners", "CIVC Partners",
        "Clayton, Dubilier & Rice", "Clearlake Capital", "Colony Capital",
        "Court Square Capital Partners", "Crescent Capital Group", "CrossHarbor Capital Partners",
        "Crossroads Group", "Cypress Group", "Defoe Fournier & Cie.",
        "Diamond Castle Holdings", "DLJ Merchant Banking Partners",
        "EIG Global Energy Partners", "Elevation Partners", "EnCap Investments",
        "Energy Capital Partners", "Fenway Partners", "First Reserve Corporation",
        "Forstmann Little & Company", "Fortress Investment Group",
        "Fox Paine & Company", "Francisco Partners", "Freeman Spogli & Co.",
        "Fremont Group", "Friedman Fleischer & Lowe", "Frontenac Company",
        "General Atlantic", "Genstar Capital", "GI Partners", "Golden Gate Capital Partners",
        "Goldman Sachs Capital Partners", "Gores Group", "GP Investimentos",
        "GTCR", "H.I.G. Capital", "Hamilton Lane", "Harbert Management Corporation",
        "HarbourVest Partners", "Harvest Partners", "Heartland Industrial Partners",
        "Hellman & Friedman", "Highbridge Capital Management", "Highland Capital Management",
        "HM Capital Partners", "HPS Investment Partners", "InterMedia Partners",
        "Irving Place Capital", "J.H. Whitney & Company", "J.W. Childs Associates",
        "JC Flowers", "JLL Partners", "Jordan Company", "Kelso & Company",
        "Khosla Ventures", "Kinderhook Industries", "Kleiner Perkins", "Kohlberg & Company",
        "KPS Capital Partners", "L Catterton", "Landmark Partners", "Lee Equity Partners",
        "Leeds Equity Partners", "Leonard Green & Partners", "Lexington Partners",
        "Lightyear Capital", "Lincolnshire Management", "Lindsay Goldberg Bessemer",
        "Littlejohn & Co.", "Lone Star Funds", "Lovell Minnick Partners",
        "LRG Capital Funds", "Lux Capital", "Madison Dearborn Partners",
        "MatlinPatterson Global Advisors", "Metalmark Capital", "MidOcean Partners",
        "Morgan Stanley Private Equity", "New Mountain Capital", "NRDC Equity Partners",
        "Oak Hill Capital Partners", "Oak Investment Partners", "Olympus Partners",
        "One Equity Partners", "Onex Corporation", "Pamlico Capital",
        "Pathway Capital Management", "Platinum Equity", "Providence Equity Partners",
        "Quadrangle Group", "Redpoint Ventures", "Rhône Group", "Ripplewood Holdings",
        "Riverside Partners", "Riverstone Holdings", "Roark Capital Group",
        "RPX Corporation", "Sentinel Capital Partners", "Silver Lake Partners",
        "Stonepeak", "Summit Partners", "Sun Capital Partners", "Sycamore Partners",
        "Symphony Technology Group", "TA Associates", "Tavistock Group", "TCV",
        "Thayer Hidden Creek", "Thoma Bravo", "Thoma Cressey Bravo",
        "Thomas H. Lee Partners", "Tiger Global Management", "TowerBrook Capital Partners",
        "TPG Capital", "Trilantic Capital Partners", "Trivest", "TSG Consumer Partners",
        "Värde Partners", "Veritas Capital", "Veronis Suhler Stevenson",
        "Vestar Capital Partners", "Vista Equity Partners", "Vivo Capital",
        "Vulcan Capital Management", "Warburg Pincus", "Warwick Energy Group",
        "Welsh, Carson, Anderson & Stowe", "Wesray Capital Corporation",
        "Weston Presidio", "Willis Stein & Partners", "Wind Point Partners",
        "WL Ross & Co.", "Yucaipa Cos.", "Zelnick Media Capital",
        "3i", "Actis", "AlpInvest Partners", "Altor Equity Partners", "Apax Partners",
        "Arcapita", "Ardian", "Argentum Fondsinvesteringer", "Axcel", "Aurelius Group",
        "Baring Vostok Capital Partners", "BC Partners", "BIP Investment Partners",
        "Bridgepoint Capital", "Butler Capital Partners", "CapMan", "Capital Dynamics",
        "Capvis", "Charterhouse Capital Partners", "Cinven", "Close Brothers Group",
        "Coller Capital", "Conquest Asset Management", "Copenhagen Infrastructure Partners",
        "C.W. Obel", "CVC Capital Partners", "Doughty Hanson & Co", "DST Global",
        "Dubai International Capital", "Duke Street Capital", "EMVest Asset Management",
        "EQT AB", "Eurazeo", "Ferd", "Fondinvest Capital", "GFH Capital", "GIMV",
        "Graphite Capital", "GK Investment", "HgCapital", "ICT Group", "Idinvest Partners",
        "IFD Kapital Group", "IK Investment Partners", "Infinity Group",
        "Intermediate Capital Group", "Investcorp", "Jadwa Investment", "Kennet Partners",
        "Kistefos", "LGT Capital Partners", "Livingbridge", "M. Goldschmidt Holding",
        "Marfin Investment Group", "MerchantBridge", "Meyer Bergman",
        "Mid Europa Partners", "Mubadala Investment Company", "Mutares", "Nordic Capital",
        "Norfund", "OpCapita", "PAI Partners", "Pantheon Ventures", "Partners Group",
        "Permira", "Phoenix Equity Partners", "Ratos", "Silverfleet Capital Partners",
        "SL Capital Partners", "Sofina", "SVG Capital", "Terra Firma Capital Partners",
        "Unbound Group", "Vitruvian Partners"
    ]

def get_default_public_asset_managers():
    """Returns a default list of public asset managers for the blocklist."""
    return {
        "managers": [
            "BlackRock", "The Vanguard Group", "Vanguard Group", "Fidelity Investments", 
            "State Street Global Advisors", "SSGA", "Morgan Stanley Investment Management", 
            "J.P. Morgan Asset Management", "JPMorgan Chase", "Goldman Sachs Asset Management", 
            "Goldman Sachs Group", "Capital Group", "The Capital Group Companies", 
            "Capital International Investors", "Amundi", "Crédit Agricole", "UBS Asset Management", 
            "UBS", "BNY Mellon Investment Management", "BNY Investments", "Allianz Global Investors", 
            "Allianz Group", "PIMCO", "Deutsche Bank", "DWS Group", "Invesco", "Franklin Templeton", 
            "Legal & General", "Northern Trust", "Prudential Financial", "T. Rowe Price", 
            "T. Rowe Price Group", "BNP Paribas Asset Management", "Natixis Investment Managers", 
            "Schroders", "Axa Investment Managers", "Generali Group", "Union Investment", "abrdn", 
            "AllianceBernstein", "Allspring Global Investments", "American Century Investments", 
            "Ameriprise Financial", "Bridgewater Associates", "Brookfield Asset Management", 
            "Charles Schwab Investment Management", "Columbia Threadneedle Investments", 
            "Dimensional Fund Advisors", "Dodge & Cox", "Eaton Vance", "Federated Hermes", 
            "Fisher Investments", "Geode Capital Management", "Janus Henderson", "Loomis, Sayles & Company", 
            "Lord, Abbett & Co.", "Manulife Investment Management", "MFS Investment Management", 
            "Neuberger Berman", "Nuveen", "PGIM", "Pzena Investment Management", "Raymond James", 
            "Russell Investments", "SEI Investments", "Waddell & Reed", "Wellington Management"
        ]
    }
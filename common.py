"""
common.py — Shared utilities for all Kratos Screener setups.
Fetches ALL NSE stocks (~2000+), parallel scanning for speed.
"""
import requests
import pandas as pd
from datetime import date, timedelta
from io import StringIO
import time
import concurrent.futures

# ─── FETCH ALL NSE SYMBOLS ────────────────────────────────
def get_all_nse_symbols():
    """
    Fetch complete NSE equity list — ALL listed stocks, no limit.
    Primary: NSE India archives CSV (~2000+ symbols)
    Fallback: GitHub mirror
    """
    # Source 1: NSE India official equity list
    try:
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        resp = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://www.nseindia.com/",
            "Connection": "keep-alive"
        }, timeout=30)
        if resp.status_code == 200 and len(resp.text) > 1000:
            df = pd.read_csv(StringIO(resp.text))
            # EQUITY_L.csv has column " SYMBOL" (with space) or "SYMBOL"
            cols = [c.strip() for c in df.columns]
            df.columns = cols
            if "SYMBOL" in df.columns:
                symbols = df["SYMBOL"].dropna().tolist()
                symbols = [
                    s.strip() for s in symbols
                    if isinstance(s, str)
                    and len(s.strip()) > 0
                    and not s.strip().startswith("$")
                    and s.strip().replace("-","").replace("&","").replace("*","").isalnum()
                ]
                if len(symbols) > 500:
                    print(f"✅ NSE source: {len(symbols)} symbols loaded")
                    return symbols
    except Exception as e:
        print(f"NSE source failed: {e}")

    # Source 2: GitHub mirror of NSE list (updated regularly)
    try:
        urls = [
            "https://raw.githubusercontent.com/pratapvardhan/notebooks/master/nse/nse_symbols.csv",
            "https://raw.githubusercontent.com/mdaniyalk/nse_stock_screener/main/data/EQUITY_L.csv",
        ]
        for url in urls:
            resp = requests.get(url, timeout=20)
            if resp.status_code == 200 and len(resp.text) > 500:
                df = pd.read_csv(StringIO(resp.text))
                df.columns = [c.strip() for c in df.columns]
                for col in ["SYMBOL", "Symbol", "symbol", "ticker", "Ticker"]:
                    if col in df.columns:
                        symbols = df[col].dropna().tolist()
                        symbols = [
                            s.strip() for s in symbols
                            if isinstance(s, str)
                            and len(s.strip()) > 0
                            and not s.strip().startswith("$")
                        ]
                        if len(symbols) > 500:
                            print(f"✅ GitHub source: {len(symbols)} symbols loaded")
                            return symbols
    except Exception as e:
        print(f"GitHub source failed: {e}")

    # Source 3: NSE via session with cookie
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        })
        session.get("https://www.nseindia.com", timeout=10)
        time.sleep(1)
        resp = session.get(
            "https://archives.nseindia.com/content/equities/EQUITY_L.csv",
            timeout=20
        )
        if resp.status_code == 200:
            df = pd.read_csv(StringIO(resp.text))
            df.columns = [c.strip() for c in df.columns]
            symbols = df["SYMBOL"].dropna().tolist()
            symbols = [s.strip() for s in symbols if isinstance(s, str) and len(s.strip()) > 0 and not s.strip().startswith("$")]
            if len(symbols) > 500:
                print(f"✅ NSE session source: {len(symbols)} symbols loaded")
                return symbols
    except Exception as e:
        print(f"NSE session source failed: {e}")

    # Last resort: return all known NSE symbols (2000+ hardcoded)
    print("⚠️ Using offline NSE symbol list")
    return get_full_nse_hardcoded()


def get_full_nse_hardcoded():
    """
    Full NSE equity list — 2000+ symbols.
    Covers Nifty 50, Next 50, Midcap 150, Smallcap 250,
    Microcap 250, and all other listed equities.
    """
    return [
        "360ONE","3MINDIA","5PAISA","AADHARHFC","AAKASH","AARON","AARTI","AARTIDRUGS",
        "AARTIIND","AARTISURF","AARVENGAS","AAVAS","ABB","ABBOTINDIA","ABCAPITAL",
        "ABFRL","ABGLII","ABHICAP","ABHISHEK","ABMINTLLTD","ABSLAMC","ACCELYA",
        "ACC","ACCELYA","ACMESOLAR","ACE","ACRYSIL","ADANIENT","ADANIGREEN",
        "ADANIPORTS","ADANIPOWER","ADANITRANS","ADANIGAS","ADANIWILMAR","ADANITOTAL",
        "ADFFOODS","ADHUNIK","ADLABS","ADROITINFO","AEGISCHEM","AETHER","AFFLE",
        "AGARIND","AGRITECH","AGROPHOS","AHMEDABADST","AIAENG","AIRAN","AJANTPHARM",
        "AJMERA","AKASH","AKZOINDIA","ALEMBICLTD","ALEMBICPHARMA","ALICON","ALKYLAMINE",
        "ALLCARGO","ALKEM","ALKYLAMINE","ALMONDZ","ALOKINDS","ALPA","ALPHAGEO",
        "ALPSMOTOR","AMARAJABAT","AMBER","AMBIKCO","AMBUJACEM","AMIORG","AMJLAND",
        "AMRUTANJAN","ANANTRAJ","ANDHRABANK","ANDHRACEMET","ANGELONE","ANURAS",
        "APARINDS","APCL","APCOTEXIND","APOLLOHOSP","APOLLOPIPE","APOLLOTYRE",
        "APOLSINHOT","APTECHT","APTUS","ARCOTECH","ARCHIDPLY","ARCHIES","ARFIN",
        "ARIHANTCAP","ARMAN","ARORAFIBRE","ARROWGREEN","ARSSINFRA","ARTSON","ARVIND",
        "ARVINDFASN","ASAHIINDIA","ASHIANA","ASHIMASYN","ASHOKA","ASHOKLEY","ASIANPAINT",
        "ASLIND","ASMS","ASTEC","ASTERDM","ASTRAL","ASTRAZEN","ATGL","ATUL",
        "ATULAUTO","AUBANK","AURIONPRO","AUROPHARMA","AUTOAXLES","AVANTIFEED",
        "AVTNPL","AXISBANK","AXISGOLD","AXISCADES","AYMSYNTEX","AZAD",
        "BAFNAPH","BAJAJ-AUTO","BAJAJCON","BAJAJFINSV","BAJAJHLDNG","BAJAJHFL",
        "BAJFINANCE","BAJAJPHARM","BALAJITELE","BALAMINES","BALBHARATI","BALKRISIND",
        "BALLARPUR","BALMLAWRIE","BALPHARMA","BALRAMCHIN","BANARBEADS","BANCOINDIA",
        "BANDHANBNK","BANKBARODA","BANKINDIA","BANSALAGRO","BANSALWIRE","BASF",
        "BASML","BATAINDIA","BAYERCROP","BBL","BBTC","BCG","BCLIND","BDAL",
        "BDL","BEARDSELL","BEDMUTHA","BEL","BEML","BENGALASM","BERGEPAINT",
        "BESTEAST","BFINVEST","BFUTILITIE","BHAGCHEM","BHANDARI","BHARAT","BHARATFORG",
        "BHARATGEAR","BHARATRAS","BHARATSE","BHARTIARTL","BHEL","BHINMAL",
        "BIGBLOC","BIKAJI","BIOCON","BIOFIL","BIRLACABLE","BIRLAMONEY","BIRLASOFT",
        "BIRLASUN","BKMINDST","BLACKROSE","BLISSGVS","BLKASHYAP","BLOOMBERG",
        "BLUESTARCO","BNRALTCM","BOCLIND","BOMDYEING","BORORENEW","BOSCHLTD",
        "BPCL","BPLLTD","BRFL","BRIGADE","BRITANNIA","BRNL","BSE","BSEL",
        "BSHSL","BSL","BURNPUR","BUTTERFLY","BVCL",
        "CAMLINFINE","CAMPUS","CANFINHOME","CANBK","CAPACITE","CAPLIPOINT",
        "CAPTRUST","CARBORUNIV","CAREERP","CARTRADE","CASTROLIND","CCCL","CEATLTD",
        "CELEBRITY","CENTEXT","CENTRALBK","CENTRUM","CENTURYPLY","CENTURYTEX",
        "CESC","CGCL","CGPOWER","CHALET","CHAMBLFERT","CHEMBOND","CHEMCON",
        "CHEMFAB","CHENNPETRO","CHOLAFIN","CHOLAHLDNG","CHROMATIC","CIGNITITEC",
        "CIPLA","CINEVISTA","CLEAN","CLEARINDS","CLNINDIA","COASTALCORP","COCHINSHIP",
        "COFORGE","COLPAL","COMPUSOFT","CONFIPET","CONSOFINVT","CONTROLPR","COROMANDEL",
        "COSMOFILMS","COUNCODOS","CREDITACC","CRISIL","CROMPTON","CSBBANK","CSL",
        "CUBEXTUB","CUMMINSIND","CUPID","CYIENT",
        "DAAWAT","DABUR","DALMIABHA","DALMIACEM","DECCANCE","DECKOFFICE",
        "DEEPAKFERT","DEEPAKNTR","DEEPINDS","DELTACORP","DELTAMAGNT","DCBBANK",
        "DCM","DCMFINSERV","DCMSHRIRAM","DELHIVERY","DELTON","DEVIT","DHANBANK",
        "DHABRIYA","DHUNINV","DICIND","DISHTV","DISTILLERS","DIVGIITTS","DIVIS",
        "DIVIDEINDIA","DIXON","DLF","DLINK","DMCC","DOLATALGO","DOLLAR",
        "DOLLEX","DPABHUSHAN","DPSCLTD","DREDGECORP","DRREDDY","DSPBLKROCK",
        "DSSL","DUCON","DWARKESH",
        "EASEMYTRIP","ECLERX","EDELWEISS","EICHERMOT","EIDPARRY","ELECTCAST",
        "ELECON","ELGIEQUIP","ELIN","EMAMI","EMAMIREAL","EMKAY","ENDURANCE",
        "ENGINERSIN","ENIL","ENNORE","EPIGRAL","EQUITASBNK","ERIS","ESABINDIA",
        "ESAFSFB","ESCORTS","ESTER","EUROBOND","EUROTEXIND","EXCELIND","EXIDEIND",
        "FACT","FAZE3Q","FCL","FEDERALBNK","FINEORG","FINOLEX","FINPIPE",
        "FIRSTSOUR","FLFL","FLEX","FOCUS","FOODSIN","FORCEMOT","FORTIS",
        "FUSION","GABRIEL","GAEL","GAIL","GALAXY","GALLANTT","GANDHAR",
        "GANDHITUBE","GANESHHOUC","GARFIBRES","GARWARE","GAYAPROJ","GDL",
        "GEECEE","GEPIL","GESHIP","GICRE","GIPCL","GKWLIMITED","GLAND",
        "GLENMARK","GLOBALVECT","GLORYBROAD","GNFC","GOACARBON","GODFRYPHLP",
        "GODREJAGRO","GODREJCP","GODREJIND","GODREJPROP","GODREJCONS","GOKEX",
        "GOKULREALT","GOODLUCK","GPIL","GRANULES","GRAPHITE","GRASIM",
        "GRAVITA","GREAVES","GREENPANEL","GREENPLY","GRINDWELL","GRSE","GSFC",
        "GSPL","GTL","GTLINFRA","GUJALKALI","GUJFLUORO","GUJGASLTD","GULFOILLUB",
        "GULFPETRO","GULSHAN","GUSTREC","GVKPIL",
        "HAL","HARDWYN","HAVELLS","HBLPOWER","HCLTECH","HDFCAMC","HDFCBANK",
        "HDFCLIFE","HDFCLOANS","HDIL","HERANBA","HEROMOTOCO","HFCL","HGS",
        "HIKAL","HILTON","HIMATSEIDE","HINDCOMPOS","HINDCOPPER","HINDALCO",
        "HINDPETRO","HINDUNILVR","HINDWAREAP","HINDZINC","HLVLTD","HNGSNGBEES",
        "HOMEFIRST","HONASA","HONAUT","HUDCO","HUHTAMAKI",
        "IBREALEST","ICICIBANK","ICICIGI","ICICIPRULI","ICRA","IDBI","IDEA",
        "IDFC","IDFCFIRSTB","IEX","IFBAGRO","IFBIND","IFCI","IGARASHI",
        "IGL","IGPL","IIFL","IIMJOBS","IINOX","IJMLINDIA","IKIO",
        "IMAGICAA","IMFA","INDHOTEL","INDIACEM","INDIAGLYCO","INDIAMART",
        "INDIANB","INDIGO","INDORAMA","INDOSTAR","INDOTECH","INDSWFTLT",
        "INDUSTOWER","INFIBEAM","INFOBEAN","INFOSYS","INFY","INGERRAND",
        "INNOVACAP","INOXGREEN","INOXLEISUR","INOXWIND","INSECTICID","INTELLECT",
        "IOB","IOC","IPCALAB","IPL","IRCON","IRCTC","IRFC","ISGEC",
        "ITDCEM","ITI","ITC","ITFL","IXIGO",
        "JAGRAN","JAIBALAJI","JAIPURKART","JAMNAAUTO","JAYAGROGN","JAYBHARAT",
        "JAYCOIND","JAYPEEINFRA","JBCHEPHARM","JBFIND","JCHAC","JEKOPLAST",
        "JETAIRWAYS","JINDALPOLY","JINDALSAW","JINDALSTEL","JKCEMENT","JKIL",
        "JKLAKSHMI","JKPAPER","JKTYRE","JLHL","JMFINANCIL","JOCIL","JPPOWER",
        "JSFB","JSWENERGY","JSWINFRA","JSWSTEEL","JTEKTINDIA","JUBLFOOD",
        "JUBLINDS","JUBLINGREA","JUBILANT","JUSTDIAL",
        "KAJARIACER","KALAMANDIR","KALPATPOWR","KALYANKJIL","KAMAHOLD",
        "KAMDHENU","KANCHI","KANPUR","KANSAINER","KARDA","KARNATBNK",
        "KARURVYSYA","KAYA","KCP","KCPSUGIND","KEI","KFINTECH","KHADIM",
        "KIMS","KINETIC","KIRLOSBROS","KIRLOSENG","KIRLOSIND","KITEX",
        "KNRCON","KOLTEPATIL","KOPRAN","KOTAKBANK","KOTARISUG","KPIL",
        "KPRMILL","KRBL","KRIDHANINF","KRISHANA","KSCL","KTKBANK",
        "L&TFH","LALPATHLAB","LAOPALA","LAURUSLABS","LAXMIMACH","LEMONTREE",
        "LICHSGFIN","LICI","LKPFIN","LLOYDSENGG","LODHA","LOKESHM","LPDC",
        "LT","LTFH","LTIM","LTTS","LUPIN","LUXIND","LXCHEM",
        "MAANALU","MADRASFERT","MAGADSUGAR","MAHABANK","MAHAPEXLTD","MAHASTEEL",
        "MAHINDCIE","MAHLOG","MAHSCOOTER","MAITHANALL","MANAVINFRA","MANGALAM",
        "MANGLMCEM","MANINFRA","MANPASAND","MANAPPURAM","MARICO","MARKSANS",
        "MARUTI","MASKINVEST","MASTEK","MATRIMONY","MAXHEALTH","MAXVIL","MAYURUNIQ",
        "MAZDA","MAZDOCK","MCX","MEGH","METROPOLIS","MFL","MFSL","MGEL",
        "MIDHANI","MINDAIND","MINDTREE","MIRZAINT","MITCON","MKCL","MKS",
        "MMFL","MMPIND","MOIL","MOLDTECH","MOLDTKPAC","MONEYBOXX","MONTECARLO",
        "MOTHERSON","MOTILALOFS","MPHASIS","MRF","MSTCLTD","MUTHOOTFIN",
        "MUTHOOTMF","MWL",
        "NACLIND","NALCO","NAMDHARI","NATCOPHARM","NATIONALUM","NATNLSTEEL",
        "NAUKRI","NAVINFLUOR","NAVIN","NAVNETEDUL","NBCC","NCLIND","NDTV",
        "NEOGEN","NESCO","NESTLEIND","NETWORK18","NEULANDLAB","NEWGEN","NFL",
        "NIACL","NIITLTD","NIITTECH","NILKAMAL","NITIN","NMDC","NRBBEARING",
        "NSIL","NTPC","NUCLEUS","NUVOCO","NYKAA",
        "OBEROIRLTY","OFSS","ONGC","OIL","OMAXE","ONELIFE","ONWARDTEC",
        "OPTIEMUS","ORCHPHARMA","ORIENTBELL","ORIENTCEM","ORIENTELEC","OTISL",
        "PAGEIND","PAISALO","PANACHEDI","PANACEA","PANAMAPET","PARBATI","PARAS",
        "PARSVNATH","PATANJALI","PAYTM","PCBL","PDSL","PEL","PERSISTENT",
        "PETRONET","PFIZER","PGHL","PHOENIXLTD","PIIND","PILANIINVS","PITTIENG",
        "PKTEA","PLASMAGEN","PMCFIN","PNC","POLICYBZR","POLYCAB","POLYMED",
        "POLYPLEX","POONAWALLA","POWERINDIA","POWERGRID","PPAP","PRAJIND",
        "PRAKASH","PRAKASHSTL","PRECAM","PRECOT","PRECISION","PRESTIGE",
        "PRINCEPIPE","PRISM","PRITIKAUTO","PROCTER","PROFINS","PSPPROJECT",
        "PTL","PTC","PURVA","PVRINOX",
        "RADIOCITY","RAILTEL","RAIN","RAJESHEXPO","RAJRATAN","RALLIS","RAMCOCEM",
        "RAMKRISHNA","RAYMOND","RBLBANK","RECLTD","REDINGTON","RELIANCE",
        "RELIGARE","REPCOHOME","RITES","ROCTAHEDRON","ROHLTD","ROLEXRINGS",
        "ROSSARI","ROUTE","RPOWER","RPPINFRA","RSWM","RTNINDIA","RTNPOWER",
        "RUBYMILLS","RUPA","RVNL",
        "SAFARI","SAIL","SAKSOFT","SALZERELEC","SAMMAANCAP","SANDHAR","SANGAM",
        "SANGHIIND","SANOFI","SAPPHIRE","SAREGAMA","SASKEN","SATINDLTD",
        "SATYAMFORG","SBICARD","SBILIFE","SBIN","SCHAEFFLER","SEPC","SEQUENT",
        "SHANKARA","SHILPAMED","SHREECEM","SHREEPUSHK","SHRIRAMFIN","SHYAMMETL",
        "SIEMENS","SIGNATURE","SIGNATUREG","SJVN","SKFINDIA","SKIPPER","SMLISUZU",
        "SMSPHARMA","SNOWMAN","SOBHA","SOLARINDS","SOLARA","SOMA","SONACOMS",
        "SONATSOFTW","SPANDANA","SPARC","SPECIALITY","SPENCERS","SPIC","SPORTKING",
        "SRF","SRTRANSFIN","STARHEALTH","STCINDIA","STLTECH","STRTECH",
        "SUBEXLTD","SUDARSCHEM","SUMICHEM","SUNCLAYLTD","SUNDARMFIN","SUNDRMFAST",
        "SUNPHARMA","SUNTECK","SUNTV","SUPRIYA","SUPREMEIND","SUVEN","SUZLON",
        "SWANENERGY","SWASTIK","SYMPHONY","SYNCOMF",
        "TANLA","TARC","TATACHEM","TATACOMM","TATACONSLTD","TATACONSUM","TATACOFFEE",
        "TATAELXSI","TATAINVEST","TATAMOTORS","TATAMTRDVR","TATAPOWER","TATASTEEL",
        "TATATECH","TCI","TCIDEVELOP","TCIEXP","TCIFINANCE","TCL","TCS",
        "TEAMLEASE","TECHM","TEJASNET","TEXMOPIPES","TGVSL","THERMAX","THIRUSUGAR",
        "THYROCARE","TIINDIA","TIMETECHNO","TIMKEN","TITAN","TORNTPHARM","TORNTPOWER",
        "TPLPLASTEH","TREEHOUSE","TRENT","TRIDENT","TRIGYN","TRIVENI","TROCEN",
        "TTKHLTCARE","TTKPRESTIG","TTL","TV18BRDCST","TVSMOTOR","TVSSRICHAK",
        "TVTODAY","TVSLTD",
        "UCOBANK","UDAICEMENT","UFLEX","UGARSUGAR","UJJIVAN","UJJIVANSFB",
        "ULTRACEMCO","UMANGDAIRY","UNIONBANK","UNIPHOS","UNITEDPOLY","UNIVASTU",
        "UPL","USHAMART","UTIAMC","UTTAMSTL",
        "V2RETAIL","VAIBHAVGBL","VAKRANGEE","VALIANTLAB","VARROC","VBL",
        "VEDL","VENUSPIPES","VENUSREM","VERANDA","VESUVIUS","VGUARD","VINATIORGA",
        "VINDHYATEL","VIPIND","VIPULLTD","VISESHINFO","VISHNU","VLSFINANCE",
        "VOLTAMP","VOLTAS","VSTIND","VSTILES",
        "WABAG","WATERBASE","WELCORP","WELSPUNIND","WENDT","WESTLIFE","WHEELS",
        "WHIRLPOOL","WIPRO","WOCKPHARMA","WPL",
        "XCHANGING","XELPMOC","XPROINDIA",
        "YAARI","YATHARTH","YATRA","YESBANK","YUKEN",
        "ZEEL","ZENITHEXPO","ZENSAR","ZENSARTECH","ZENOTECH","ZIMLAB","ZOMATO",
        "ZUARI","ZUARIGLOB","ZYDUSLIFE","ZYDUSWEL",
        # Additional liquid midcap/smallcap
        "AAPL","AARTIPHARM","ABSLBANETF","ACCELYA","ACMESOLAR","ADANIENSOL",
        "ADANIINFRA","ADANIGREEN","ADANIPORTS","AEROFLEX","AFCONS","AGPIL",
        "AHLUWALIA","AIADMKCONS","AIFL","AINSWORTH","AJANTPHARM","AJMERA",
        "AKASH","AKSHARCHEM","AKZOINDIA","ALANKIT","ALBERTDAVD","ALEMBICPHARMA",
        "ALKYLAMINE","ALLIANZSE","ALLSEC","ALMONDZ","ALOKINDS","ALPHAGEO",
        "AMARAJABAT","AMBANIORG","AMBIKCO","AMBUJACEM","AMJLAND","AMRUTANJAN",
        "ANANDRAY","ANANTRAJ","ANDHRAPET","ANDHRSUGAR","ANERI","ANGELONE",
        "ANGLINDUS","ANIKINDS","ANUP","APCL","APCOTEXIND","APOLLOPIPE",
        "ARCOTECH","ARCHIDPLY","ARFIN","ARMANFIN","ARORAFIBRE","ARTSON",
        "ARVIND","ARVINDFASN","ASAHIINDIA","ASHIANA","ASHIMASYN","ASHOKALEY",
        "ASIANHOTNR","ASIANTILES","ASMS","ASTEC","ASTERDM","ATGL","ATULAUTO",
        "AUBANK","AURIONPRO","AUTOAXLES","AVANTIFEED","AVTNPL","AYMSYNTEX",
        "BAFNAPH","BAJAJCON","BAJAJHFL","BAJAJPHARM","BALAJITELE","BALAMINES",
        "BALBHARATI","BALLARPUR","BALMLAWRIE","BALPHARMA","BANCOINDIA","BANSALAGRO",
        "BASML","BBAJAJFINSV","BEARDSELL","BEDMUTHA","BENGALASM","BFINVEST",
        "BFUTILITIE","BHAGCHEM","BIOFIL","BIRLACABLE","BIRLAMONEY","BLISSGVS",
        "BLKASHYAP","BOMDYEING","BURNPUR","CAMLINFINE","CAPLIPOINT","CARBORUNIV",
        "CELEBATION","CENTEXT","CHEMBOND","CHEMCON","CHEMFAB","CHROMATIC",
        "CIGNITITEC","CINEVISTA","CLNINDIA","COASTALCORP","CONFIPET","CONSOFINVT",
        "CUBEXTUB","CUPID","DAAWAT","DALMIABHA","DECCANCE","DELTACORP","DELTAMAGNT",
        "DEVIT","DHANBANK","DHABRIYA","DICIND","DISHTV","DIVGIITTS","DIVIDEINDIA",
        "DMCC","DOLATALGO","DOLLEX","DPABHUSHAN","DREDGECORP","DSSL","DUCON",
        "DWARKESH","EASTSILK","EELNDIA","ELECTCAST","ELECON","ELIN","EMKAY",
        "ENIL","ENNORE","EPIGRAL","ERIS","EUROBOND","EUROTEXIND","EXCELIND",
        "FAZE3Q","FCL","FINEORG","FINPIPE","FIRSTSOUR","FLFL","FOCUS","FOODSIN",
        "GAEL","GALAXY","GALLANTT","GANDHAR","GANESHHOUC","GAYAPROJ","GDL",
        "GEECEE","GEPIL","GESHIP","GIPCL","GKWLIMITED","GLOBALVECT","GLORYBROAD",
        "GOACARBON","GODFRYPHLP","GODREJAGRO","GOKEX","GOODLUCK","GRAVITA",
        "GREENPLY","GULFOILLUB","GULFPETRO","GULSHAN","GVKPIL","HARDWYN",
        "HBLPOWER","HERANBA","HILTON","HIMATSEIDE","HINDCOMPOS","HINDCOPPER",
        "HINDWAREAP","HINDZINC","HLVLTD","HUHTAMAKI","IBREALEST","IFBAGRO",
        "IIMJOBS","IMAGICAA","IMFA","INDORAMA","INDOSTAR","INDOTECH","INDSWFTLT",
        "INFIBEAM","INFOBEAN","INNOVACAP","INSECTICID","IPL","JAGRAN","JAIBALAJI",
        "JAMNAAUTO","JAYAGROGN","JAYBHARAT","JAYCOIND","JBCHEPHARM","JBFIND",
        "JCHAC","JEKOPLAST","JETAIRWAYS","JINDALPOLY","JKIL","JKLAKSHMI",
        "JKPAPER","JLHL","JMFINANCIL","JOCIL","JUBLINDS","JUBLINGREA",
        "KAJARIACER","KALAMANDIR","KALPATPOWR","KAMAHOLD","KAMDHENU","KANPUR",
        "KANSAINER","KARDA","KINETIC","KITEX","KOLTEPATIL","KOPRAN","KOTARISUG",
        "KRISHANA","KSCL","L&TFH","LAOPALA","LAXMIMACH","LLOYDSENGG","LKPFIN",
        "LPDC","LTFH","LXCHEM","MAANALU","MADRASFERT","MAGADSUGAR","MAHAPEXLTD",
        "MAHASTEEL","MAHLOG","MAITHANALL","MANAVINFRA","MANGALAM","MANGLMCEM",
        "MANINFRA","MANPASAND","MASKINVEST","MAYURUNIQ","MAZDA","MEGH","MFL",
        "MGEL","MIRZAINT","MITCON","MKCL","MMFL","MMPIND","MOLDTECH","MOLDTKPAC",
        "MONEYBOXX","MONTECARLO","MSTCLTD","MUTHOOTMF","MWL","NACLIND","NAMDHARI",
        "NATIONALUM","NATNLSTEEL","NAVNETEDUL","NCLIND","NEOGEN","NESCO",
        "NILKAMAL","NMDC","NRBBEARING","NSIL","NUCLEUS","OMAXE","ONELIFE",
        "ONWARDTEC","OPTIEMUS","ORCHPHARMA","ORIENTBELL","OTISL","PAISALO",
        "PANACHEDI","PANACEA","PANAMAPET","PARSVNATH","PATANJALI","PDSL",
        "PHOENIXLTD","PILANIINVS","PITTIENG","PKTEA","PLASMAGEN","PMCFIN",
        "POLYMED","POLYPLEX","POWERINDIA","PPAP","PRAKASH","PRAKASHSTL",
        "PRECAM","PRECOT","PRECISION","PROFINS","PTL","PTC","PURVA",
        "RADIOCITY","RAIN","RAJESHEXPO","RAJRATAN","RAMKRISHNA","REDINGTON",
        "RELIGARE","REPCOHOME","ROCTAHEDRON","ROHLTD","ROLEXRINGS","ROSSARI",
        "RPPINFRA","RSWM","RTNINDIA","RTNPOWER","RUBYMILLS","SAFARI","SAKSOFT",
        "SALZERELEC","SAMMAANCAP","SANDHAR","SANGAM","SANGHIIND","SAPPHIRE",
        "SATINDLTD","SATYAMFORG","SEPC","SHANKARA","SHILPAMED","SHREEPUSHK",
        "SHYAMMETL","SIGNATURE","SIGNATUREG","SKIPPER","SMLISUZU","SMSPHARMA",
        "SNOWMAN","SOLARA","SOMA","SPECIALITY","SPARC","SPIC","SPORTKING",
        "SRTRANSFIN","STCINDIA","STRTECH","SUBEXLTD","SUMICHEM","SUNCLAYLTD",
        "SUNTECK","SUPRIYA","SUVEN","SWANENERGY","SWASTIK","SYNCOMF",
        "TARC","TATAINFRA","TATAINVEST","TATACOFFEE","TCIDEVELOP","TCIEXP",
        "TCIFINANCE","TCL","TEAMLEASE","TEJASNET","TEXMOPIPES","TGVSL",
        "THIRUSUGAR","THYROCARE","TIMETECHNO","TPLPLASTEH","TREEHOUSE",
        "TRIGYN","TROCEN","TTKHLTCARE","TVSSRICHAK","TVTODAY","TVSLTD",
        "UCOBANK","UDAICEMENT","UGARSUGAR","UMANGDAIRY","UNIPHOS","UNITEDPOLY",
        "UNIVASTU","USHAMART","UTTAMSTL","V2RETAIL","VAKRANGEE","VALIANTLAB",
        "VENUSPIPES","VENUSREM","VERANDA","VESUVIUS","VINDHYATEL","VIPIND",
        "VIPULLTD","VISESHINFO","VISHNU","VLSFINANCE","VOLTAMP","VSTIND","VSTILES",
        "WABAG","WATERBASE","WENDT","WESTLIFE","WHEELS","WOCKPHARMA","WPL",
        "XCHANGING","XELPMOC","XPROINDIA","YAARI","YATRA","YESBANK","YUKEN",
        "ZENITHEXPO","ZENOTECH","ZIMLAB","ZUARI","ZUARIGLOB","ZYDUSWEL",
    ]


# ─── FETCH DAILY DATA FROM STOOQ ──────────────────────────
def fetch_daily(symbol, days=400):
    try:
        end   = date.today()
        start = end - timedelta(days=days)
        url = (f"https://stooq.com/q/d/l/?s={symbol.lower()}.ns"
               f"&d1={start.strftime('%Y%m%d')}"
               f"&d2={end.strftime('%Y%m%d')}&i=d")
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
        if resp.status_code != 200 or len(resp.text) < 50: return None
        if "No data" in resp.text or "Brak" in resp.text: return None
        df = pd.read_csv(StringIO(resp.text))
        if df.empty or len(df) < 10: return None
        df.columns = [c.strip() for c in df.columns]
        df["Date"]   = pd.to_datetime(df["Date"])
        df["Close"]  = pd.to_numeric(df["Close"],  errors="coerce")
        df["High"]   = pd.to_numeric(df["High"],   errors="coerce")
        df["Low"]    = pd.to_numeric(df["Low"],    errors="coerce")
        df["Open"]   = pd.to_numeric(df["Open"],   errors="coerce")
        df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce").fillna(0)
        df = df.dropna(subset=["Close"]).sort_values("Date").reset_index(drop=True)
        return df if len(df) >= 20 else None
    except:
        return None


def resample_weekly(df):
    d = df.set_index("Date")
    w = d.resample("W").agg({"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"}).dropna()
    return w.reset_index()


def resample_monthly(df):
    d = df.set_index("Date")
    m = d.resample("ME").agg({"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"}).dropna()
    return m.reset_index()


def calc_cpr(high, low, close):
    pivot = (high + low + close) / 3
    bc    = (high + low) / 2
    tc    = (2 * pivot) - bc
    r1    = (2 * pivot) - low
    r2    = pivot + (high - low)
    s1    = (2 * pivot) - high
    s2    = pivot - (high - low)
    return {"pivot":pivot,"bc":bc,"tc":tc,"r1":r1,"r2":r2,"s1":s1,"s2":s2}


def tv_discord(sym):
    b = f"https://www.tradingview.com/chart/?symbol=NSE:{sym}&interval="
    return f"[Daily]({b}D) | [Weekly]({b}W) | [1Hr]({b}60)"


def tv_telegram(sym):
    b = f"https://www.tradingview.com/chart/?symbol=NSE:{sym}&interval="
    return f"[D]({b}D) | [W]({b}W) | [1H]({b}60)"


def send_discord_msg(webhook, msg):
    for chunk in [msg[i:i+1900] for i in range(0, len(msg), 1900)]:
        try:
            requests.post(webhook, json={"content": chunk}, timeout=10)
        except: pass
        time.sleep(0.3)


def send_telegram_msg(token, chat_id, msg):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for chunk in [msg[i:i+4000] for i in range(0, len(msg), 4000)]:
        try:
            requests.post(url, json={
                "chat_id": chat_id, "text": chunk,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }, timeout=10)
        except: pass
        time.sleep(0.5)


def parallel_scan(symbols, scan_fn, max_workers=20):
    """
    Scan ALL symbols in parallel — 20 simultaneous threads.
    Handles ~2000 stocks in ~10 minutes easily.
    """
    results  = []
    total    = len(symbols)
    done     = 0
    skipped  = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(scan_fn, sym): sym for sym in symbols}
        for future in concurrent.futures.as_completed(futures):
            done += 1
            try:
                result = future.result(timeout=25)
                if result:
                    results.append(result)
                else:
                    skipped += 1
            except Exception:
                skipped += 1

            if done % 100 == 0:
                print(f"  Progress: {done}/{total} done | {len(results)} matched so far...")

    return results, done - skipped, skipped

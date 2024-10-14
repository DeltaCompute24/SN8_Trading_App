from fastapi import HTTPException

from src.utils.logging import setup_logging

logger = setup_logging()

# ------------------------ PAIRS ALLOWED BY POLYGON ---------------------------------
forex_polygon_pairs = [
    'XAGEUR', 'MDLUSD', 'INRCAD', 'AUDMAD', 'AEDDKK', 'AEDUSD', 'IDRUSD', 'XAUZAR', 'VNDEUR',
    'JPYPKR', 'GBPPAB', 'CRCGBP', 'CHFCAD', 'LRDGBP', 'JPYIDR', 'RUBDKK', 'ARSHKD', 'USDDKK',
    'USDINR', 'THBTWD', 'SEKJPY', 'KRWHKD', 'BRLSGD', 'KYDUSD', 'MVRUSD', 'AUDKRW', 'EURRON',
    'GBPSCR', 'MYRTWD', 'MXNPLN', 'EURBHD', 'THBNZD', 'GBPBDT', 'NOKINR', 'GNFGBP', 'IDRZAR',
    'EURLKR', 'JPYBRL', 'GBPAMD', 'USDLRD', 'VNDUSD', 'THBCNY', 'UGXZAR', 'FJDUSD', 'PENMXN',
    'USDBZD', 'EURGNF', 'AUDTRY', 'JPYCNY', 'EURYER', 'XAUUSD', 'XAGMXN', 'GBPTWD', 'AEDCHF',
    'JPYRSD', 'ARSCOP', 'EURJMD', 'EURCOP', 'CNYAUD', 'SEKRUB', 'SEKCHF', 'NZDINR', 'DKKPKR',
    'EURGYD', 'MXNJPY', 'NGNGBP', 'CNYHKD', 'MXNSGD', 'GBPBAM', 'XAGZAR', 'GBPZMW', 'CADUSD',
    'SGDAUD', 'GBPLRD', 'UYUUSD', 'AUDCZK', 'EURETB', 'EURKRW', 'CADNZD', 'EGPZAR', 'EURCNY',
    'EURZAR', 'RWFUSD', 'AUDBRL', 'THBCAD', 'USDNAD', 'ZARRON', 'ZARMXN', 'SGDTWD', 'TZSZAR',
    'EURCLP', 'ZARPKR', 'NZDAED', 'CADCHF', 'CNYEUR', 'TRYSGD', 'CZKDKK', 'MYREUR', 'ILSEUR',
    'GBPUSD', 'CLPMXN', 'BRLMXN', 'LRDUSD', 'NPRUSD', 'GBPKZT', 'EURNOK', 'SEKDKK', 'ZARTND',
    'CZKSEK', 'AEDCAD', 'ZARJPY', 'XAGTRY', 'NOKUSD', 'KWDUSD', 'HNLGBP', 'AUDCNY', 'IDRMYR',
    'CADBMD', 'HKDAUD', 'SEKEUR', 'PLNGBP', 'ZARTWD', 'CNHHKD', 'SEKCAD', 'PGKGBP', 'USDISK',
    'CADCNY', 'MURUSD', 'CHFSGD', 'MDLEUR', 'JPYUSD', 'GYDGBP', 'MYRCHF', 'NZDDKK', 'XAUKRW',
    'USDCNH', 'TRYJPY', 'ARSEUR', 'VNDJPY', 'CADZAR', 'NZDCAD', 'SGDUSD', 'NZDTRY', 'GBPCAD',
    'USDUYU', 'GBPMOP', 'KRWNZD', 'ZARUSD', 'GBPSVC', 'GBPSZL', 'LSLGBP', 'EURCDF', 'ISKCHF',
    'EGPUSD', 'CRCUSD', 'BBDGBP', 'THBMYR', 'CLPAUD', 'USDFJD', 'CADKRW', 'EURMKD', 'USDTZS',
    'EURCZK', 'AWGGBP', 'CZKJPY', 'JPYPLN', 'CADARS', 'ZARSEK', 'ZARCNY', 'AUDAED', 'USDTJS',
    'MYRDKK', 'GBPBMD', 'EURDKK', 'JPYTHB', 'CADEUR', 'HKDCAD', 'SZLCHF', 'ARSMXN', 'NOKGBP'
]

crypto_polygon_pairs = [
    'DNTUSD', 'LCXUSD', 'XRDUSD', 'ZECUSD', 'AERGOUSD', 'RUNEUSD', 'ENJUSD', 'BONDUSD', 'ASTUSD',
    'NKNUSD', 'ONDOUSD', 'LTCAUD', 'XDCUSD', 'ALICEUSD', 'FETUSD', 'NCTUSD', 'AKTEUR', 'TLOSUSD',
    'LSKUSD', 'BCHUSD', 'NEXOUSD', 'AIOZUSD', 'GLMUSD', 'ALPHAUSD', 'AUCTIONUSD', 'WEUR', 'ZKXUSD',
    'JTOUSD', 'NEARUSD', 'BTCJPY', 'RARIUSD', 'USDCUSD', 'DIAUSD', 'YGGUSD', 'AKTUSD', 'FISUSD',
    'MKRUSD', 'SUKUUSD', 'MATICUSD', 'LYMUSD', 'MAGICUSD', 'STORJUSD', 'QIUSD', 'XVGUSD', 'LPTUSD',
    'WIFEUR', 'NMRUSD', 'DAIUSD', 'DOGEUSD', 'CGLDUSD', 'IOTUSD', 'LINKUSD', 'BONKUSD', 'TIAUSD',
    'JUPUSD', 'AAVEUSD', 'LOKAUSD', 'LITUSD', 'ORNUSD', 'VOXELUSD', 'PAXGUSD', 'JSTUSD', 'SNXUSD',
    'OXTUSD', 'UNIUSD', 'AXSUSD', 'EOSUSD', 'SGBUSD', 'OCEANUSD', 'CTSIUSD', 'PERPUSD', 'ATOMUSD',
    'ETHUSD', 'BALUSD', 'BTCUSD', 'LTCBTC', 'MDTUSD', '1INCHUSD', 'IMXUSD', 'KSMUSD', 'HNTUSD',
    'XTZUSD', 'BCHGBP', 'QTUMUSD', 'KEEPUSD', 'PNKUSD', 'SPELLUSD', 'LTCEUR', 'REPUSD', 'WBTCUSD',
    'FARMUSD', 'TSDUSD', 'UDCUSD', 'KAVAUSD', 'STRKEUR', 'MLNUSD', 'WIFUSD', 'SEIEUR', 'KRLUSD',
    'USTUSD', 'MASKUSD', 'EGLDUSD', 'GYENUSD', 'CHRUSD', 'OGNUSD', 'DUSKUSD', 'ACHUSD', 'APEUSD',
    'SHIBUSD', 'AMPUSD', 'ARPAUSD', 'BATUSD', 'DYDXUSD', 'TNSRUSD', 'FTMUSD', 'MPLUSD', 'VTHOUSD',
    'LUNAUSD', 'ABTUSD', 'CHZUSD', 'INJUSD', 'FOXUSD', 'ILVUSD', 'NANOUSD', 'CRVUSD', 'PAXUSD',
    'GALAUSD', 'COMPUSD', 'ETHBTC', 'CVCUSD', 'SWFTCUSD', 'GNOUSD', 'MNAUSD', 'XRPBTC', 'GUSDUSD',
    'CLVUSD', 'ZRXUSD', 'TRACUSD', 'REQUSD', 'PYTHUSD', 'FILUSD', 'FORTHUSD', 'FORTUSD', 'BNTUSD',
    'STRKUSD', 'ORCAUSD', 'OMGUSD', 'RLYUSD', 'RARIEUR', 'BOSONUSD', 'QTMUSD', 'SKLUSD', 'XRPAUD',
    'HBARUSD', 'AXLUSD', 'SANDUSD', 'BONKEUR', 'API3USD', 'CHREUR', 'SRMUSD', 'NEOUSD', 'DASHUSD',
    'TRXUSD', 'TVKUSD', 'AVAXUSD', 'METISUSD', 'BTRSTUSD', 'LRCUSD', 'SOLUSD', 'CROUSD', 'LTCUSD',
    'CVXUSD', 'SEIUSD', 'SUSHIUSD', 'YFIUSD', 'PYRUSD', 'ADAUSD', 'UMAUSD', 'MANAUSD', 'VELOUSD',
    'GRTUSD', 'FLOWUSD', 'BANDUSD', 'MSOLUSD', 'C98USD', 'GHSTUSD', 'RENUSD', 'MIRUSD', 'BTCEUR',
    'TRBUSD', 'SCUSD', 'BTCGBP', 'ANTUSD', 'TVKEUR', 'ROSEUSD', 'JASMYUSD', 'ICXUSD', 'PUNDIXUSD',
    'CSMUSD', 'STXUSD', 'KNCUSD', 'USDTUSD', 'DARUSD', 'XMRUSD', 'ARKMUSD', 'DSHUSD', 'BADGERUSD',
    'XYOUSD', 'IOTXUSD', 'YGGEUR', 'DOTUSD', 'OMNIUSD', 'BTCAUD', 'PRIMEUSD', 'ALCXUSD', 'ALGOUSD',
    'OXYUSD', 'HIGHUSD', 'ANKRUSD', 'UOSUSD', 'BTTUSD', 'ETHAUD', 'DYDXEUR', 'XLMUSD', 'RLCUSD',
    'ELAUSD', 'COTIUSD', 'ICPUSD', 'LQTYUSD', 'QRDOUSD', 'BCHEUR', 'BOBAUSD', 'AVTUSD', 'QNTUSD',
    'TRUUSD', 'ASMUSD', 'ETCUSD', 'RNDRUSD', 'WUSD', 'XAUTUSD', 'FXUSD', 'TUSD', 'GTCUSD', 'XRPUSD',
    'ZENUSD', 'VETUSD', 'FUNUSD'
]

# ------------------------------------ PAIRS ALLOWED BY OUR SYSTEM -------------------------------------------------
crypto_pairs = ["BTCUSD", "ETHUSD"]
forex_pairs = ["AUDCAD", "AUDUSD", "AUDJPY", "CADCHF", "CADJPY", "CHFJPY", "EURCAD", "EURUSD", "EURCHF", "EURGBP",
               "EURJPY", "EURNZD", "NZDCAD", "NZDJPY", "GBPUSD", "GBPJPY", "USDCAD", "USDCHF", "USDJPY", ]
indices_pairs = ["GDAXI", "NDX", "VIX"]


def validate_position(position, adjust=False):
    asset_type, trade_pair = validate_trade_pair(position.asset_type, position.trade_pair)
    if not adjust:
        order_type = validate_order_type(position.order_type)
        position.order_type = order_type
    position.asset_type = asset_type
    position.trade_pair = trade_pair

    if position.stop_loss is None:
        position.stop_loss = 0
    if position.take_profit is None:
        position.take_profit = 0

    return position


def validate_trade_pair(asset_type, trade_pair):
    asset_type = asset_type.lower()
    trade_pair = trade_pair.upper()

    if asset_type not in ["crypto", "forex", "indices"]:
        raise HTTPException(status_code=400, detail="Invalid asset type, It should be crypto or forex!")
    if asset_type == "crypto" and trade_pair not in crypto_pairs:
        raise HTTPException(status_code=400, detail="Invalid trade pair for asset type crypto!")
    if asset_type == "forex" and trade_pair not in forex_pairs:
        raise HTTPException(status_code=400, detail="Invalid trade pair for asset type forex!")
    if asset_type == "indices" and trade_pair not in indices_pairs:
        raise HTTPException(status_code=400, detail="Invalid trade pair for asset type indices!")

    return asset_type, trade_pair


def validate_order_type(order_type):
    order_type = order_type.upper()

    if order_type not in ["LONG", "SHORT", "FLAT"]:
        raise HTTPException(status_code=400, detail="Invalid order type, It should be long, short or flat")

    return order_type

from fastapi import HTTPException

from src.utils.logging import setup_logging

logger = setup_logging()

forex_pairs = ['XAGEUR', 'MDLUSD', 'INRCAD', 'AUDMAD', 'AEDDKK', 'AEDUSD', 'IDRUSD', 'XAUZAR', 'VNDEUR', 'JPYPKR',
               'GBPPAB', 'CRCGBP', 'CHFCAD', 'LRDGBP', 'JPYIDR', 'RUBDKK', 'ARSHKD', 'USDDKK', 'USDINR', 'THBTWD',
               'SEKJPY', 'KRWHKD', 'BRLSGD', 'KYDUSD', 'MVRUSD', 'AUDKRW', 'EURRON', 'GBPSCR', 'MYRTWD', 'MXNPLN',
               'EURBHD', 'THBNZD', 'GBPBDT', 'NOKINR', 'GNFGBP', 'IDRZAR', 'EURLKR', 'JPYBRL', 'GBPAMD', 'USDLRD',
               'VNDUSD', 'THBCNY', 'UGXZAR', 'FJDUSD', 'PENMXN', 'USDBZD', 'EURGNF', 'AUDTRY', 'JPYCNY', 'EURYER',
               'XAUUSD', 'XAGMXN', 'GBPTWD', 'AEDCHF', 'JPYRSD', 'ARSCOP', 'EURJMD', 'EURCOP', 'CNYAUD', 'SEKRUB',
               'SEKCHF', 'NZDINR', 'DKKPKR', 'EURGYD', 'MXNJPY', 'NGNGBP', 'CNYHKD', 'MXNSGD', 'GBPBAM', 'XAGZAR',
               'GBPZMW', 'CADUSD', 'SGDAUD', 'GBPLRD', 'UYUUSD', 'AUDCZK', 'EURETB', 'EURKRW', 'CADNZD', 'EGPZAR',
               'EURCNY', 'EURZAR', 'RWFUSD', 'AUDBRL', 'THBCAD', 'USDNAD', 'ZARRON', 'ZARMXN', 'SGDTWD', 'TZSZAR',
               'EURCLP', 'ZARPKR', 'NZDAED', 'CADCHF', 'CNYEUR', 'TRYSGD', 'CZKDKK', 'MYREUR', 'ILSEUR', 'GBPUSD',
               'CLPMXN', 'BRLMXN', 'LRDUSD', 'NPRUSD', 'GBPKZT', 'EURNOK', 'SEKDKK', 'ZARTND', 'CZKSEK', 'AEDCAD',
               'ZARJPY', 'XAGTRY', 'NOKUSD', 'KWDUSD', 'HNLGBP', 'AUDCNY', 'IDRMYR', 'CADBMD', 'HKDAUD', 'SEKEUR',
               'PLNGBP', 'ZARTWD', 'CNHHKD', 'SEKCAD', 'PGKGBP', 'USDISK', 'CADCNY', 'MURUSD', 'CHFSGD', 'MDLEUR',
               'JPYUSD', 'GYDGBP', 'MYRCHF', 'NZDDKK', 'XAUKRW', 'USDCNH', 'TRYJPY', 'ARSEUR', 'VNDJPY', 'CADZAR',
               'NZDCAD', 'SGDUSD', 'NZDTRY', 'GBPCAD', 'USDUYU', 'GBPMOP', 'KRWNZD', 'ZARUSD', 'GBPSVC', 'GBPSZL',
               'LSLGBP', 'EURCDF', 'ISKCHF', 'EGPUSD', 'CRCUSD', 'BBDGBP', 'THBMYR', 'CLPAUD', 'USDFJD', 'CADKRW',
               'EURMKD', 'USDTZS', 'EURCZK', 'AWGGBP', 'CZKJPY', 'JPYPLN', 'CADARS', 'ZARSEK', 'ZARCNY', 'AUDAED',
               'USDTJS', 'MYRDKK', 'GBPBMD', 'EURDKK', 'JPYTHB', 'CADEUR', 'HKDCAD', 'SZLCHF', 'ARSMXN', 'NOKGBP',
               'HKDSEK', 'TWDINR', 'EURDOP', 'MYRKRW', 'NIOGBP', 'DKKNZD', 'USDHTG', 'EURQAR', 'LKRZAR', 'RONCHF',
               'TWDMYR', 'HKDEUR', 'PENCLP', 'JPYHKD', 'GBPBWP', 'KESUSD', 'GBPPKR', 'EURDZD', 'JPYINR', 'NOKEUR',
               'CHFSZL', 'CHFAED', 'JPYNOK', 'CHFMXN', 'SGDBRL', 'ZARPLN', 'ZARAUD', 'TRYCHF', 'USDLBP', 'PENCAD',
               'AUDEUR', 'RWFZAR', 'AUDARS', 'KMFGBP', 'BWPEUR', 'CNYSGD', 'GBPBRL', 'PYGUSD', 'CNYCHF', 'GBPILS',
               'HUFCHF', 'CHFRUB', 'HKDMXN', 'CNYZAR', 'XAGGBP', 'JPYKRW', 'CNYINR', 'MGAGBP', 'XAUMXN', 'CHFCZK',
               'COPCAD', 'GBPKES', 'HNLUSD', 'GBPZAR', 'SARJPY', 'EURTHB', 'SGDIDR', 'ZARNZD', 'GTQGBP', 'USDTRY',
               'JPYILS', 'AUDPHP', 'GBPNOK', 'RUBCAD', 'SEKGBP', 'ZARHKD', 'USDILS', 'GNFUSD', 'USDCAD', 'EURCHF',
               'USDVND', 'SCRUSD', 'EURNGN', 'PLNILS', 'EURMDL', 'DKKTRY', 'CLPEUR', 'HUFCAD', 'XPFGBP', 'TWDCAD',
               'GBPJOD', 'XAUCAD', 'DKKCNY', 'RWFGBP', 'BNDGBP', 'SZLZAR', 'SARKWD', 'BMDCAD', 'CADSEK', 'PHPUSD',
               'CHFAUD', 'MOPUSD', 'PENUSD', 'XAGCNY', 'AUDTHB', 'DKKRUB', 'KRWIDR', 'KRWCAD', 'EURJOD', 'USDTND',
               'HKDKRW', 'EURBZD', 'KHRGBP', 'PENARS', 'PKRUSD', 'AEDNOK', 'EURLAK', 'EURSGD', 'TWDEUR', 'USDCOP',
               'JPYCHF', 'BDTGBP', 'KRWTHB', 'CADCZK', 'EURMGA', 'GBPMGA', 'DKKHUF', 'ARSZAR', 'CADAUD', 'CHFPKR',
               'SGDCAD', 'HUFUSD', 'INRGBP', 'IDRSGD', 'USDMZN', 'HKDMYR', 'BAMGBP', 'NZDAUD', 'IDRINR', 'EURCAD',
               'BDTUSD', 'GBPTND', 'EURARS', 'NZDNOK', 'IDRGBP', 'USDMKD', 'TJSUSD', 'BRLCHF', 'KRWINR', 'USDSZL',
               'HUFEUR', 'MYRCNY', 'BGNCNY', 'HKDTHB', 'JODUSD', 'GHSEUR', 'EURBGN', 'THBJPY', 'CHFCLP', 'NZDEUR',
               'GBPTTD', 'JPYZAR', 'PLNCHF', 'GBPINR', 'THBCHF', 'KWDEUR', 'XCDGBP', 'IDRJPY', 'EGPPKR', 'DKKAED',
               'USDTHB', 'JODAED', 'USDGTQ', 'ZARARS', 'USDKZT', 'IDREUR', 'ZARBWP', 'USDKES', 'INRUSD', 'GBPCUP',
               'CNYKRW', 'AEDINR', 'DKKHKD', 'EURBTN', 'BGNDKK', 'GBPRWF', 'EURKZT', 'GBPBZD', 'GBPCNY', 'BAMUSD',
               'TWDGBP', 'DKKPHP', 'XAUEUR', 'TWDZAR', 'GBPCRC', 'GBPBGN', 'EURMWK', 'BNDUSD', 'EURNZD', 'JPYAED',
               'ZARRUB', 'NGNUSD', 'EURTJS', 'RSDUSD', 'USDPKR', 'USDEGP', 'HUFZAR', 'AUDTWD', 'XAGUSD', 'AUDHKD',
               'USDALL', 'ZARCAD', 'GBPKMF', 'HKDARS', 'EURUSD', 'TWDUSD', 'ZARTRY', 'CNYNZD', 'AUDSGD', 'DKKAUD',
               'IDRAUD', 'JPYGBP', 'MYRUSD', 'EURHTG', 'OMRAED', 'USDRSD', 'YERGBP', 'GBPLSL', 'GBPISK', 'BMDEUR',
               'DKKISK', 'KRWGBP', 'EURMAD', 'EURTRY', 'PKRZAR', 'KRWCNY', 'GBPRON', 'PENCOP', 'SGDMXN', 'ZARKES',
               'EURBSD', 'AUDCNH', 'EURPKR', 'BRLRUB', 'HKDPKR', 'MYRAUD', 'USDZMW', 'USDPGK', 'USDOMR', 'LTLAUD',
               'USDBOB', 'ZARCZK', 'USDPEN', 'GBPTHB', 'EGPJPY', 'USDCRC', 'JMDGBP', 'ZARDKK', 'CHFEUR', 'GBPHUF',
               'THBZAR', 'EURSZL', 'CADMXN', 'MYRJPY', 'INRTWD', 'EURDJF', 'EURBRL', 'LBPUSD', 'DKKEUR', 'USDSCR',
               'CADJPY', 'EURGTQ', 'BHDUSD', 'KRWEUR', 'GBPETB', 'HKDDKK', 'EURMVR', 'GYDUSD', 'SCRGBP', 'ZARCYP',
               'AUDSEK', 'CADAED', 'CNYBGN', 'XAUSAR', 'GBPPLN', 'MKDGBP', 'NOKAED', 'SGDNOK', 'USDKYD', 'USDBSD',
               'THBINR', 'MXNCOP', 'CADVND', 'DKKMXN', 'USDMYR', 'PABUSD', 'AUDZAR', 'SARPKR', 'MXNZAR', 'THBSGD',
               'COPMXN', 'NOKCHF', 'AUDCHF', 'AMDGBP', 'AUDILS', 'XAUJPY', 'CADCOP', 'UZSUSD', 'PLNDKK', 'XAGSAR',
               'SOSUSD', 'GHSGBP', 'BWPZAR', 'IDRCNY', 'EURSAR', 'EURBDT', 'ALLGBP', 'TWDNZD', 'EURHUF', 'ZARNOK',
               'SGDHKD', 'NOKPLN', 'PENBRL', 'NPRGBP', 'GBPNPR', 'HKDUSD', 'TWDHKD', 'KYDCAD', 'KZTUSD', 'USDGYD',
               'DKKZAR', 'ZARCHF', 'SGDEUR', 'USDUAH', 'GBPNZD', 'EURMXN', 'DKKCZK', 'SGDCHF', 'ZARSGD', 'USDRUB',
               'EURCNH', 'EGPEUR', 'DKKPLN', 'GBPCNH', 'DKKGBP', 'ILSZAR', 'USDTTD', 'CLPARS', 'EURTWD', 'BRLEUR',
               'GBPCZK', 'JPYCZK', 'HKDSGD', 'CADGBP', 'IDRNZD', 'MYRPKR', 'BMDKYD', 'NZDSGD', 'ARSCHF', 'USDNPR',
               'RUBSEK', 'SGDNZD', 'GBPAFN', 'JPYMYR', 'GBPJMD', 'KWDAED', 'CADRUB', 'GBPNGN', 'DKKBGN', 'EURILS',
               'EURLYD', 'EURBIF', 'PKREUR', 'DKKUSD', 'GBPBOB', 'GBPKRW', 'TNDUSD', 'NZDCHF', 'CHFCNY', 'GBPCOP',
               'CNYJPY', 'MXNHKD', 'USDMUR', 'OMRGBP', 'AUDCAD', 'RUBEUR', 'BGNCAD', 'DKKSGD', 'BRLRSD', 'ARSPEN',
               'RUBUSD', 'EURAUD', 'GBPSEK', 'SAREUR', 'GBPUAH', 'DKKTWD', 'HKDTWD', 'OMRUSD', 'XAUTRY', 'MYRNZD',
               'EURBMD', 'AUDMYR', 'HKDGBP', 'SGDDKK', 'INRTHB', 'USDBRL', 'USDBHD', 'USDLAK', 'ILSCAD', 'UAHDKK',
               'KRWSEK', 'CLPGBP', 'EURUZS', 'SEKILS', 'GBPRSD', 'GBPBIF', 'PLNHUF', 'CHFTWD', 'BRLARS', 'SEKNOK',
               'USDUZS', 'CLPCNY', 'KMFUSD', 'GBPARS', 'AEDAUD', 'USDNGN', 'EURINR', 'BZDUSD', 'BGNAUD', 'USDIQD',
               'NZDPLN', 'HTGUSD', 'CHFMYR', 'CADSAR', 'NADUSD', 'EUREGP', 'EURAED', 'AUDUSD', 'ALLEUR', 'USDPYG',
               'GBPOMR', 'IDRHKD', 'GBPEUR', 'TWDPKR', 'SGDZAR', 'GBPRUB', 'INRJPY', 'MXNBRL', 'NZDTHB', 'CNYGBP',
               'NGNZAR', 'PHPJPY', 'DKKNOK', 'XAUTHB', 'EURMUR', 'BOBGBP', 'MUREUR', 'EURLSL', 'CADBRL', 'EURAFN',
               'DKKJPY', 'GBPLKR', 'ZARGBP', 'CYPZAR', 'CZKZAR', 'BDTJPY', 'SEKPLN', 'INRAUD', 'CADTHB', 'USDQAR',
               'EURPEN', 'DKKCAD', 'TRYPLN', 'GHSUSD', 'LKRUSD', 'CZKUSD', 'USDKMF', 'KRWAUD', 'GBPPYG', 'EURUGX',
               'CNYCLP', 'NZDJPY', 'XAURUB', 'CHFUSD', 'PLNMXN', 'EURRWF', 'USDLSL', 'SGDTRY', 'XAGBRL', 'KESZAR',
               'CLPUSD', 'BSDGBP', 'RUBKRW', 'ARSCAD', 'PLNJPY', 'GBPCHF', 'USDCZK', 'TZSUSD', 'GBPEGP', 'TWDSGD',
               'SEKUSD', 'GBPSAR', 'JPYCLP', 'THBPKR', 'EURKES', 'USDIDR', 'MXNEUR', 'SEKCZK', 'USDAED', 'EUROMR',
               'BHDPKR', 'USDKRW', 'CADKWD', 'TWDKRW', 'NIOUSD', 'ZARGHS', 'ILSSEK', 'COPUSD', 'KRWCHF', 'TRYDKK',
               'KRWZAR', 'ZAREUR', 'THBIDR', 'HUFPLN', 'JODILS', 'USDMGA', 'UYUEUR', 'CLPCHF', 'EURPYG', 'EURNPR',
               'SGDTHB', 'SZLGBP', 'PLNEUR', 'EURRUB', 'CADMYR', 'USDDZD', 'CHFSEK', 'DKKUAH', 'BTNGBP', 'GBPDOP',
               'BOBUSD', 'DKKCHF', 'XAGRUB', 'JPYNZD', 'CZKEUR', 'SGDAED', 'CHFBRL', 'MYRHKD', 'GBPMAD', 'BRLKRW',
               'QARZAR', 'ZARILS', 'ZARAED', 'EURUYU', 'ARSAUD', 'XAGAUD', 'ZARCOP', 'EURVND', 'GBPKHR', 'EURSDG',
               'CADNOK', 'RSDGBP', 'NOKJPY', 'GBPGHS', 'EURHKD', 'USDGMD', 'CNHJPY', 'ZARIDR', 'CLPBRL', 'SZLUSD',
               'CHFJPY', 'EURBOB', 'CHFRSD', 'MXNCHF', 'GBPPHP', 'MYRINR', 'USDGBP', 'TWDCNY', 'USDCVE', 'HKDZAR',
               'HKDCHF', 'XAGINR', 'TRYZAR', 'DZDUSD', 'AEDSAR', 'USDMAD', 'NZDHKD', 'CADPLN', 'GBPMDL', 'SGDJPY',
               'INRPKR', 'EURZMW', 'CHFHKD', 'AUDNZD', 'SGDCNY', 'ZARRWF', 'MXNUSD', 'USDGNF', 'AUDINR', 'KRWRUB',
               'MXNAUD', 'USDRON', 'CZKNOK', 'SGDMYR', 'TWDJPY', 'USDHKD', 'INREUR', 'CHFHUF', 'BBDEUR', 'ARSUSD',
               'USDBAM', 'ILSPLN', 'CHFILS', 'QARAED', 'DZDEUR', 'EURTZS', 'NZDIDR', 'SGDINR', 'INRKRW', 'EURTTD',
               'CHFTRY', 'RUBCHF', 'GBPLYD', 'KRWTWD', 'LYDGBP', 'KRWMYR', 'USDTWD', 'EURSVC', 'USDEUR', 'CHFNOK',
               'INRCNY', 'GBPDZD', 'JPYSEK', 'USDETB', 'RUBGBP', 'AUDDKK', 'EURSOS', 'BIFUSD', 'XAUAUD', 'SGDGBP',
               'GBPLAK', 'USDSEK', 'ARSGBP', 'DKKINR', 'ILSAUD', 'GBPTRY', 'KRWSGD', 'PHPDKK', 'BMDGBP', 'IDRCAD',
               'HKDNZD', 'USDKHR', 'HUFJPY', 'XAGARS', 'GBPCDF', 'GBPNIO', 'CUPUSD', 'ZARTHB', 'THBKRW', 'ETBUSD',
               'USDAUD', 'EURBWP', 'EURPLN', 'ZARINR', 'CADBGN', 'HKDPLN', 'CADPKR', 'CHFGBP', 'GBPYER', 'MYRCAD',
               'EURUAH', 'ILSAED', 'BRLHKD', 'ZMWZAR', 'USDRWF', 'RONGBP', 'EURCUP', 'GBPXCD', 'EURLBP', 'ETBGBP',
               'CHFARS', 'AUDNOK', 'NZDGBP', 'MXNDKK', 'AUDPKR', 'USDNOK', 'MYRIDR', 'GBPLBP', 'CADKYD', 'USDCHF',
               'PGKUSD', 'RUBNOK', 'SGDPKR', 'ZARSZL', 'USDNZD', 'RUBZAR', 'IDRTWD', 'INRNZD', 'USDNIO', 'ILSCHF',
               'INRSGD', 'GBPKYD', 'SARUSD', 'EURPHP', 'EURHNL', 'AEDZAR', 'VNDCAD', 'KRWUSD', 'TRYUSD', 'USDBDT',
               'EURKHR', 'RONZAR', 'USDCLP', 'LKRGBP', 'THBHKD', 'CNYDKK', 'AEDBHD', 'CHFPLN', 'LYDUSD', 'MYRTHB',
               'MADGBP', 'GBPQAR', 'AUDPGK', 'BRLCOP', 'SVCGBP', 'MXNARS', 'EURKWD', 'BSDUSD', 'EURPGK', 'NZDUSD',
               'EURMYR', 'NOKDKK', 'QARGBP', 'SVCUSD', 'AUDBGN', 'GBPPGK', 'TWDSEK', 'CADPEN', 'AUDPLN', 'MADAUD',
               'IQDGBP', 'XAUINR', 'ZAREGP', 'NOKRUB', 'CHFINR', 'ISKUSD', 'XAGHKD', 'MZNUSD', 'NZDSEK', 'IDRKRW',
               'AUDLTL', 'AEDSEK', 'PGKAUD', 'EURALL', 'EURLRD', 'LSLUSD', 'KWDGBP', 'GBPSOS', 'EURCRC', 'AEDNZD',
               'AUDCLP', 'TWDIDR', 'AUDGBP', 'USDARS', 'USDSOS', 'CLPPEN', 'AEDPKR', 'NZDKRW', 'GBPBSD', 'CHFZAR',
               'USDJPY', 'XAUBRL', 'MXNCZK', 'MADZAR', 'JPYARS', 'USDDJF', 'AEDJPY', 'EURGHS', 'EURNAD', 'GBPKWD',
               'CHFTHB', 'BRLCAD', 'USDLKR', 'AEDEUR', 'THBAUD', 'TTDGBP', 'KRWJPY', 'EURRSD', 'CDFGBP', 'CZKCAD',
               'INRZAR', 'DJFGBP', 'PKRGBP', 'GBPMYR', 'XAUCNY', 'HKDCNY', 'CADILS', 'USDMDL', 'CADTRY', 'RUBMXN',
               'GBPDJF', 'TTDUSD', 'GHSZAR', 'HKDIDR', 'GTQUSD', 'TWDDKK', 'HKDJPY', 'RUBPLN', 'NZDMXN', 'PLNSEK',
               'CZKMXN', 'AUDFJD', 'PLNNOK', 'USDHUF', 'PKRJPY', 'ZARUGX', 'AUDHUF', 'USDJMD', 'USDZAR', 'CADINR',
               'USDBWP', 'XAGKRW', 'GBPSGD', 'USDXPF', 'XAUARS', 'SGDKRW', 'MXNGBP', 'ZARPHP', 'COPDKK', 'CHFKRW',
               'DKKCOP', 'THBUSD', 'MXNRUB', 'USDSVC', 'NOKZAR', 'USDPLN', 'ARSJPY', 'INRMYR', 'GBPMKD', 'SGDPLN',
               'CHFDKK', 'EURKYD', 'EURMZN', 'CADHKD', 'EURGBP', 'ZARNAD', 'GBPBBD', 'CHFBWP', 'USDMXN', 'HUFDKK',
               'USDMVR', 'GBPIQD', 'ILSJOD', 'BWPCHF', 'BRLCLP', 'CNYUSD', 'AUDJPY', 'TNDGBP', 'ILSNOK', 'TWDAUD',
               'XAGCAD', 'GBPALL', 'AFNGBP', 'XAUGBP', 'EURNIO', 'JMDUSD', 'AUDMXN', 'GBPAUD', 'PENEUR', 'DOPUSD',
               'ZARBRL', 'GBPIDR', 'USDSGD', 'NOKSEK', 'EURIQD', 'USDJOD', 'USDUGX', 'GBPBND', 'MYRZAR', 'HTGGBP',
               'MXNCAD', 'BRLAUD', 'GBPGNF', 'IQDUSD', 'TWDCHF', 'KYDEUR', 'INRHKD', 'GBPXPF', 'CZKCHF', 'SZLEUR',
               'COPCLP', 'ZARKRW', 'GBPMUR', 'USDHNL', 'PLNUSD', 'JPYMXN', 'ZARNGN', 'JPYCAD', 'CLPCOP', 'USDPHP',
               'SGDSEK', 'GBPCLP', 'XAUHKD', 'SOSGBP', 'OMRPKR', 'USDLYD', 'THBGBP', 'ARSSGD', 'ILSJPY', 'EURBBD',
               'GBPUGX', 'CADTWD', 'RUBJPY', 'MXNPEN', 'GBPMXN', 'GBPGTQ', 'GBPPEN', 'GBPHTG', 'COPZAR', 'INRSEK',
               'EURSEK', 'BRLUSD', 'FJDGBP', 'ARSCLP', 'JPYEUR', 'ILSUSD', 'BRLZAR', 'PLNCZK', 'ZARMAD', 'GBPJPY',
               'USDKWD', 'SEKAUD', 'CNYCAD', 'GBPVND', 'USDPAB', 'MKDUSD', 'HKDBRL', 'TNDZAR', 'USDGHS', 'NOKILS',
               'USDSAR', 'KZTGBP', 'USDCUP', 'BGNUSD', 'TWDTHB', 'PENGBP', 'GBPAED', 'DKKMYR', 'USDDOP', 'MGAUSD',
               'ZARHUF', 'GBPBHD', 'ZARMYR', 'ALLUSD', 'COPBRL', 'BMDBBD', 'JPYSAR', 'AEDGBP', 'EURMOP', 'GBPFJD',
               'COPARS', 'SEKZAR', 'BWPGBP', 'BBDUSD', 'QARPKR', 'DOPGBP', 'BRLPEN', 'NZDPKR', 'XAGJPY', 'DKKSEK',
               'IDRTHB', 'IDRCHF', 'BHDEUR', 'USDBGN', 'DKKTHB', 'MURGBP', 'ARSBRL', 'CADSGD', 'GBPUYU', 'SGDARS',
               'EURTND', 'NZDCZK', 'CNHUSD', 'PHPGBP', 'CADDKK', 'HKDINR', 'EURIDR', 'CHFNZD', 'GBPHKD', 'USDCDF',
               'CADHUF', 'JPYDKK', 'NGNJPY', 'MDLGBP', 'GBPBTN', 'MYRSGD', 'GBPAWG', 'EURPAB', 'KYDBMD', 'AUDIDR',
               'CDFUSD', 'EURJPY', 'KYDGBP', 'THBEUR', 'CHFRON', 'OMRZAR', 'USDBBD', 'JPYAUD', 'CADIDR', 'NZDZAR',
               'UYUGBP', 'NZDHUF', 'USDCNY', 'USDMOP', 'BRLJPY', 'INRCHF', 'NZDMYR', 'CHFIDR', 'SEKINR', 'USDBIF',
               'MXNCLP', 'NZDCNY', 'EURAMD', 'RONUSD', 'GBPHNL', 'NZDTWD', 'BRLSEK', 'JPYTWD', 'EURBND', 'BWPUSD',
               'JPYRUB', 'GBPDKK', 'UAHUSD', 'ZMWUSD', 'MYRGBP', 'EURSCR', 'MADUSD', 'GBPMVR', 'CZKPLN', 'GBPGYD',
               'USDBND', 'EURFJD', 'KRWBRL']

crypto_pairs = ['DNTUSD', 'LCXUSD', 'XRDUSD', 'ZECUSD', 'AERGOUSD', 'RUNEUSD', 'ENJUSD', 'BONDUSD', 'ASTUSD', 'NKNUSD',
                'ONDOUSD', 'LTCAUD', 'XDCUSD', 'ALICEUSD', 'FETUSD', 'NCTUSD', 'AKTEUR', 'TLOSUSD', 'LSKUSD', 'BCHUSD',
                'NEXOUSD', 'AIOZUSD', 'GLMUSD', 'ALPHAUSD', 'AUCTIONUSD', 'WEUR', 'ZKXUSD', 'JTOUSD', 'NEARUSD',
                'BTCJPY',
                'RARIUSD', 'USDCUSD', 'DIAUSD', 'YGGUSD', 'AKTUSD', 'FISUSD', 'MKRUSD', 'SUKUUSD', 'MATICUSD', 'LYMUSD',
                'MAGICUSD', 'STORJUSD', 'QIUSD', 'XVGUSD', 'LPTUSD', 'WIFEUR', 'NMRUSD', 'DAIUSD', 'DOGEUSD', 'CGLDUSD',
                'IOTUSD', 'LINKUSD', 'BONKUSD', 'TIAUSD', 'JUPUSD', 'AAVEUSD', 'LOKAUSD', 'LITUSD', 'ORNUSD',
                'VOXELUSD',
                'PAXGUSD', 'JSTUSD', 'SNXUSD', 'OXTUSD', 'UNIUSD', 'AXSUSD', 'EOSUSD', 'SGBUSD', 'OCEANUSD', 'CTSIUSD',
                'PERPUSD', 'ATOMUSD', 'ETHUSD', 'BALUSD', 'BTCUSD', 'LTCBTC', 'MDTUSD', '1INCHUSD', 'IMXUSD', 'KSMUSD',
                'HNTUSD', 'XTZUSD', 'BCHGBP', 'QTUMUSD', 'KEEPUSD', 'PNKUSD', 'SPELLUSD', 'LTCEUR', 'REPUSD', 'WBTCUSD',
                'FARMUSD', 'TSDUSD', 'UDCUSD', 'KAVAUSD', 'STRKEUR', 'MLNUSD', 'WIFUSD', 'SEIEUR', 'KRLUSD', 'USTUSD',
                'MASKUSD', 'EGLDUSD', 'GYENUSD', 'CHRUSD', 'OGNUSD', 'DUSKUSD', 'ACHUSD', 'APEUSD', 'SHIBUSD', 'AMPUSD',
                'ARPAUSD', 'BATUSD', 'DYDXUSD', 'TNSRUSD', 'FTMUSD', 'MPLUSD', 'VTHOUSD', 'LUNAUSD', 'ABTUSD', 'CHZUSD',
                'INJUSD', 'FOXUSD', 'ILVUSD', 'NANOUSD', 'CRVUSD', 'PAXUSD', 'GALAUSD', 'COMPUSD', 'ETHBTC', 'CVCUSD',
                'SWFTCUSD', 'GNOUSD', 'MNAUSD', 'XRPBTC', 'GUSDUSD', 'CLVUSD', 'ZRXUSD', 'TRACUSD', 'REQUSD', 'PYTHUSD',
                'FILUSD', 'FORTHUSD', 'FORTUSD', 'BNTUSD', 'STRKUSD', 'ORCAUSD', 'OMGUSD', 'RLYUSD', 'RARIEUR',
                'BOSONUSD',
                'QTMUSD', 'SKLUSD', 'XRPAUD', 'HBARUSD', 'AXLUSD', 'SANDUSD', 'BONKEUR', 'API3USD', 'CHREUR', 'SRMUSD',
                'NEOUSD', 'DASHUSD', 'TRXUSD', 'TVKUSD', 'AVAXUSD', 'METISUSD', 'BTRSTUSD', 'LRCUSD', 'SOLUSD',
                'CROUSD',
                'LTCUSD', 'CVXUSD', 'SEIUSD', 'SUSHIUSD', 'YFIUSD', 'PYRUSD', 'ADAUSD', 'UMAUSD', 'MANAUSD', 'VELOUSD',
                'GRTUSD', 'FLOWUSD', 'BANDUSD', 'MSOLUSD', 'C98USD', 'GHSTUSD', 'RENUSD', 'MIRUSD', 'BTCEUR', 'TRBUSD',
                'SCUSD', 'BTCGBP', 'ANTUSD', 'TVKEUR', 'ROSEUSD', 'JASMYUSD', 'ICXUSD', 'PUNDIXUSD', 'CSMUSD', 'STXUSD',
                'KNCUSD', 'USDTUSD', 'DARUSD', 'XMRUSD', 'ARKMUSD', 'DSHUSD', 'BADGERUSD', 'XYOUSD', 'IOTXUSD',
                'YGGEUR',
                'DOTUSD', 'OMNIUSD', 'BTCAUD', 'PRIMEUSD', 'ALCXUSD', 'ALGOUSD', 'OXYUSD', 'HIGHUSD', 'ANKRUSD',
                'UOSUSD',
                'BTTUSD', 'ETHAUD', 'DYDXEUR', 'XLMUSD', 'RLCUSD', 'ELAUSD', 'COTIUSD', 'ICPUSD', 'LQTYUSD', 'QRDOUSD',
                'BCHEUR', 'BOBAUSD', 'AVTUSD', 'QNTUSD', 'TRUUSD', 'ASMUSD', 'ETCUSD', 'RNDRUSD', 'WUSD', 'XAUTUSD',
                'FXUSD',
                'TUSD', 'GTCUSD', 'XRPUSD', 'ZENUSD', 'VETUSD', 'FUNUSD']


def validate_position(position):
    asset_type, trade_pair = validate_trade_pair(position.asset_type, position.trade_pair)
    order_type = validate_order_type(position.order_type)
    position.asset_type = asset_type
    position.trade_pair = trade_pair
    position.order_type = order_type
    return position



def validate_trade_pair(asset_type, trade_pair):
    asset_type = asset_type.lower()
    trade_pair = trade_pair.upper()

    if asset_type not in ["crypto", "forex"]:
        logger.error("Invalid asset type, It should be crypto or forex!")
        raise HTTPException(status_code=400, detail="Invalid asset type, It should be crypto or forex!")
    if asset_type == "crypto" and trade_pair not in crypto_pairs:
        logger.error("Invalid trade pair for asset type crypto!")
        raise HTTPException(status_code=400, detail="Invalid trade pair for asset type crypto!")
    if asset_type == "forex" and trade_pair not in forex_pairs:
        logger.error("Invalid trade pair for asset type forex!")
        raise HTTPException(status_code=400, detail="Invalid trade pair for asset type forex!")

    return asset_type, trade_pair


def validate_order_type(order_type):
    order_type = order_type.upper()

    if order_type not in ["LONG", "SHORT", "FLAT"]:
        logger.error("Invalid order type, It should be long, short or flat")
        raise HTTPException(status_code=400, detail="Invalid order type, It should be long, short or flat")

    return order_type

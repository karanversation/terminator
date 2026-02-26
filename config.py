"""
Configuration for Transaction Analyzer
Contains category rules and application constants
"""

# =======================
# APPLICATION CONSTANTS
# =======================
DATA_DIR = "source_files"  # folder containing all CSV/TXT/XLS files

# =======================
# CATEGORIZATION RULES - EXPENSES (DEBITS)
# =======================
# Note: Keywords are matched using a scoring system:
# - Longer, more specific keywords get higher scores
# - Multi-word phrases get bonus scores
# - Exact word matches get bonus scores
# - Put more specific keywords first for better organization
EXPENSE_CATEGORY_RULES = {
    'Grocery & Supplies': [
        # Grocery delivery and online stores
        'r:zepto\s*(marketplace|now)?',  # Matches: zepto, zeptonow, zepto now, zepto marketplace
        'blinkit', 'bigbasket', 'grofers', 'jiomart',
        'dunzo', 'milk basket', 'nature\'s basket', 'more supermarket',
        # Supermarkets and local stores
        'avenue supermarts', 'reliance fresh', 'reliance smart', 'dmart', 'star bazaar',
        'spencer', 'walmart', 'foodhall', 'sainsburys', 'sainsbury',
        # Generic grocery keywords
        'grocery', 'supermarket', 'provisions', 'supplies', 'kirana'
    ],
    'Food & Dining': [
        # Specific restaurants and food chains (more specific first)
        'truffles hospitality', 'salt restaurant', 'carnatic cafe', 'pind balluchi',
        'bade miya', 'beejapuri dairy', 'sinoel foods', 'social  noida', 'social ',
        'blue tokai', 'bikanervala', 'costa coffee', 'cooks corner', 'avocado greens',
        'connaught plaza restau', 'flo at church', 'glued',
        # Food delivery apps and parent companies
        'fresh to home', 'freshtohome', 'uber eats', 'razorpay licious',
        'zomato', 'swiggy', 'dineout', 'licious',
        # Eternal Limited = parent company of Zomato & Blinkit (listed since Jan 2025)
        'eternal',
        # Food chains
        'mcdonald', 'domino', 'starbucks', 'smoor', 'mithaas',
        # Generic food keywords (less specific, lower priority due to length)
        'restaurant', 'restaura',  # 'restaura' = truncated "restaurant" in bank statements
        'pizza', 'burger', 'bakery', 'cafe', 'coffee', 'dining',
        'beverage', 'beverages',
        'food', 'kfc', 'chai', 'tea', 'sweets',
        'mithai',     # Indian sweets
        'rajaji haveli',  # restaurant/hotel
        'o\'neills', 'okkio',  # pubs/cafes abroad
        'phuong vu',  # Vietnamese restaurant
        'green ways',  # grocery/food store
    ],
    'Transportation': [
        # Specific fuel stations (multi-word, more specific)
        'gaurs energy station', 'r:(om sai|shriom|rathee)\s*filling\s*(station|point)?',
        'essar saroorpur fillin', 'filling station', 'filling statio', 'filling point',
        'petrol pump', 'gaurs energy', 'hp petrol', 'indian oil', 'essar',
        'dolly motors',  # vehicle service/purchase
        'lul ticket',    # London Underground ticket machine
        'onthego express',  # roadside vehicle assistance
        'towell auto',   # car rental abroad
        # Specific drivers/cab services
        'kailash mum cab', 'vishesh kumar', 'sabzar ahmad', 'mohd  haroon',
        'gaurav kumar', 'kalpana rani', 'blu smart',
        # Ride apps
        'ubertrip', 'olacabs', 'rapido', 'r:grab[\*\s]?',  # Matches: grab*, grab
        # General transportation
        'fastag', 'parking', 'diesel', 'petrol', 'fuel', 'metro', 'toll',
        'uber', 'taxi', 'ola', 'cab'
    ],
    'Shopping': [
        'vr precision optics', 'amazon', 'flipkart', 'myntra', 'ajio', 'meesho',
        'westside', 'tata cliq', 'decathlon', 'mall', 'store', 'shoppers',
        'reliance', 'smart baby', 'titan', 'dyson', 'apple', 'samsung', 'croma',
        'vijay sales', 'shop', 'retail', 'lifestyle', 'pantaloons', 'max fashion',
        'h&m', 'zara', 'uniqlo', 'googleplay', 'google play', 'playstore',
        'app store', 'optics', 'optical', 'eyewear',
        'wakefit',       # furniture/bedding
        'nearbuy',       # deal-of-the-day platform
        'ringke',        # phone accessories
        'apparel', 'apparels',   # clothing stores
        'parkcity sporting',  # sports equipment/facility
        'mr diy',        # DIY hardware store
        'dvdp technologies',  # tech products
        'kent',          # water purifier/appliance brand
    ],
    'Utilities & Bills': [
        # Specific utility providers (from actual transactions)
        'r:upi-n(oida power corporat|pcl-paytm)', 'billdeskpg.npcl', 'noidapower billdesk', 
        'noidapower', 'noida power',
        'upi-indraprastha gas', 'billdeskpg.indr', 'indraprastha gas',
        'r:cloud4things(esb)?', 'r:tata\s*play(fiber)?',
        'electricity bill', 'power bill',
        # FASTag toll payments
        'fastag auto sweep', 'fastag',
        # Vehicle service and maintenance
        'crown honda', 'service center', 'vehicle service', 'car service',
        # Streaming and digital services
        'me dc si', 'youtubegoogle', 'netflix', 'prime', 'hotstar', 'spotify', 'youtube', 
        'playstation', 'r:billdeskpg\.appleservi|upi-apple services',
        # Telecom
        'airtel', 'vodafone', 'spaybbps',
        # Generic utilities
        'broadband', 'internet', 'electricity', 'recharge', 'utility',
        'mobile', 'water', 'jio', 'gas', 'vi', 'society maintenance'
    ],
    'Rent': [
        # Specific rent and maintenance payments
        'upi-frequip rentals', 'frequip rentals', 'appliance rental',
        'upi-mygate', 'mygate.razorpay', 'mygate.paytm',
        'upi-vivish technologies', 'vivish technologies',
        'upi-avalon rangoli', 'avalonrangoli', 'avalon',
        'radius synergies',  # co-working/office rent
        # Generic rent keywords
        'rent', 'house rent', 'maintenance', 'sayall', 'imps-521511178925-sayall'
    ],
    'Healthcare': [
        # Specific doctors and healthcare providers
        'osho dhyan mandir', 'r:(dr)?sudhir\s*hebbar', 'dr anoop',
        # Hospitals and clinics
        'hospital', 'clinic', 'doctor', 'medical', 'pharmacy', 'medicine', 'health',
        'apollo', 'max', 'fortis', 'tata memorial', 'alora pharmacy', 'specialist opd',
        'gynae', 'meds', 'kailash healthcare', 'tata 1mg', 'modern health',
        'dental', 'diagnostic', 'lab test', 'pathology', 'dr ', 'uma medicare',
        'salon', 'spa', 'gym', 'fitness', 'yoga', 'r:cult(\.)?fit',
        'personal care', 'grooming', 'wellness', 'beauty', 'cosmetics',
        'lakme', 'nykaa', 'mamaearth', 'the body shop', 'haircut', 'fittr',
        'pharmeasy', 'netmeds', 'medlife', 'meditation', 'dhyan'
    ],
    'Travel': [
        # Visa and travel services
        'sanjay gupta', 'mindways', 'atlys', 'visa services', 'visa fee', 'visa application',
        'vfsglobal', 'vfs global', 'r:ease\s*my\s*trip',
        # Travel booking platforms
        'ibibo group', 'goibibo', 'r:irctc(\.easebuzz)?', 'makemytrip', 'make my trip', 'cleartrip',
        'klook',  # Klook travel experiences
        # Flights and hotels
        'flight', 'hotel', 'airbnb', 'oyo', 'booking', 'agoda', 'yatra', 'taj',
        'le travenue', 'airport', 'lounge', 'loung',  # 'loung' = truncated "lounge" in bank stmts
        'enterprise rent-a-car', 'car rental',
        'ritz carlton', 'passport', 'itc gardenia', 'rcb front office', 'airways',
        'duty free', 'dcc transaction', 'int.driversassociation',
        'bazpackers', 'kickassgrassmarket', 'foreign travel', 'international',
        'virgin atlantic', 'goibibo flight', 'e-visa', 'evisa', 'airline',
        'british airways', 'emirates', 'indigo', 'spicejet', 'air india',
        'vistara', 'etihad', 'lufthansa', 'klm', 'qatar airways', 'airindia',
        'heathrow', 'euston', 'train', 'railway', 'rail ticket',
        'r:british\s+a\d{10,}',  # British Airways truncated flight number (BRITISH A1252211173257257)
    ],
    'Investments': [
        # Standing instructions and automatic investments (specific patterns from bank statements)
        'r:^si hga[ifghp]p\w*',  # Matches: SI HGAIP, SI HGAFP, SI HGAGP, SI HGAHP with optional suffix
        'standing instruction',
        # Mutual fund investments (ACH Debit patterns)
        'ach d- ppfas', 'ppfas', 'cams',
        # Investment platforms and products
        'mutual fund', 'sip', 'stock', 'equity', 'trading', 
        'r:(upi-)?zerodha broking', 'zerodha', 'groww',
        'upstox', 'paytm money', 'r:(upi-)?stable broking', 'stable money',
        'shares', 'demat', 'nfl ncd', 'cshfrest', 'bond',
        'fixed deposit', 'fd '
    ],
    'Forex': [
        # Specific forex providers and transactions (must be checked before generic transfers)
        'r:imps-\d+-airwallex',  # Matches: imps-500616750132-airwallex, imps-502019675057-airwallex, etc.
        'airwallex hong kong', 'airwallex',
        'r:(razp)?book\s*my\s*forex',  # Matches: bookmyforex, book my forex, razpbookmyforex
        # Generic forex keywords
        'foreign exchange', 'forex', 'currency exchange', 'inw ', 
        'usd', 'eur', 'gbp', 'sgd', 'fcy markup', 'dcc ', 'foreign currency'
    ],
    'Credit Card Payment': [
        # Credit card bill payments (specific patterns)
        'billdkhdfccard', 'zhdf6ur0a4yh10/billdkhdfccard',
        'upi-credclub', 'upi-cred club', 'credclub@icici', 'cred.club@axisb',
        # BBPS via Axis/HDFC UPI for bill payments
        'billpay.axb', 'billpay.hdf', 'bhim app-billpay', 'hdfc bank bbps',
        # CRED app payment (PayU/CRED gateway)
        'payucredclub', 'credclub',
        # Generic credit card payments
        'ib billpay', 'hdfceb', 'billpay dr', 'icicieb', 'sbieb', 'axieb',
        'imobile pay', 'cc payment', 'card payment', 'redgiraffe', 'red giraffe',
        'credit card'
    ],
    'ATM Withdrawal': [
        # Specific ATM/cash withdrawal patterns from bank statements
        'nwd-', 'atw-', 'cash withdrawal', 'atm withdrawal', 'atm with', 'cash wdl'
    ],
    'Transfers': [
        # Specific transfer patterns (family, personal)
        'yeida rps', 'yeida refund',
        'neft dr-utib0003100-priya axis-sandoz', 'priya axis-sandoz',
        'neft dr-icic0000192-mum icici-sandoz', 'mum icici-sandoz',
        'imps-506721103532-abhilasha singh', 'abhilasha singh',
        'sangeeta', 'family transfer',
        # Generic transfer patterns (but NOT forex/airwallex)
        'neft dr-', 'rtgs dr-', 'fund transfer', 'upi transfer',
        'netbanking transfer',
        # UPI Lite wallet top-up and returns
        'upi-lite', 'upiret',
        # Cheque clearing
        'to clearing', 'clg-',
        # Loan/credit card payments to other banks
        'dcb bank', 'dcbniyosa',
        # Generic RTGS wire transfers to other institutions (e.g. Ratnakar/RBL)
        'ratnakar bank', 'rbl r',
        # UPI payments to individuals — detected by VPA pattern:
        # personal VPAs: @ok*, @pt* (Paytm), @ybl, @kkbk, @axl, @ibk, @gpay, @ptybl
        'r:upi-[\w\s]+-[\w.-]+@ok[\w]*',           # @okicici, @okhdfc, @okhdfcbank, @OKHD (truncated)
        'r:upi-[\w\s]+-[\w.-]+@pt[\w]*',            # @ptyes, @ptys, @ptybl, @pthdfc (Paytm VPAs)
        'r:upi-[\w\s]+-[\w.-]+@(ybl|ikwi|axl|ibk|pz|mairt|alfa|ptybl)',
        # Phone-number VPA = personal payment (e.g. UPI-PERSON-9999123456@YBL)
        'r:upi-[\w\s]+-\d{9,10}[\w.-]*@',
        # Google Pay VPA (gpay-XXXXXXXXXX)
        'r:upi-[\w\s]+-gpay-\d+',
        # BharatPe and Paytm QR codes (personal/micro-merchant)
        'r:upi-[\w\s]+-bharatpe\.',
        'r:upi-[\w\s]+-paytmqr[\w]+',              # Paytm QR (no @ required — truncated)
        # HDFC UPI autopay / NA description
        'r:upi-na-na-hdfc\d+',
        # Note: Forex/Airwallex uses specific IMPS patterns listed in Forex category
    ],
    'Entertainment': [
        'book my show', 'bookmyshow', 'movie', 'cinema', 'pvr', 'inox',
        'theatre', 'concert', 'event', 'game', 'gaming', 'steam',
        'playstation', 'xbox', 'nintendo', 'paytm insider', 'spotify',
        'warner bros', 'warnerbros',  # Warner Bros Studio tickets/experiences
        'konfhub',   # tech conference platform
        'tickertape',  # stock market platform/subscription
        'zettlediageo', 'diageo',  # liquor/beverages abroad
        'underdoggs',  # sports bar/restaurant
    ],
    'Taxes': [
        'income tax', 'tax payment', 'itr', 'tds', 'gst', 'advance tax',
        'tax filing', 'cleartax', 'tin nsdl',
        'cbdt',  # Central Board of Direct Taxes — appears in advance tax payments
    ],
    'Insurance': [
        # Specific insurance companies and products (multi-word, more specific)
        'r:hdfc\s*ergo(\s*billdesk)?', 'alyve health', 'health insurance', 
        'term insurance', 'policy premium', 'hdfc life', 'icici pru', 
        'bajaj allianz', 'star health', 'max life', 'r:www\s*acko\s*com', 'religare',
        # Generic insurance keywords
        'insurance', 'premium', 'policy', 'alyve', 'acko', 'lic'
    ],
    'Education': [
        'school', 'college', 'university', 'tuition', 'course', 'udemy',
        'coursera', 'learning', 'education', 'training', 'certification',
        'books', 'stationery', 'admission fee', 'tuition fee'
    ],
    'Fees & Charges': [
        'service charge', 'processing fee', 'late fee', 'penalty',
        'convenience fee', 'maintenance charge', 'annual fee', 'gst',
        'sms charge', 'debit card fee', 'non maintain', 'card reissue',
        'reissue fee', 'card charges',
        # International transaction markup fees from Diners/Regalia
        'fcy markup', 'dc intl', 'intl markup', 'pos txn markup', 'atm markup',
        'foreign txn fee', 'cross currency', 'markup fee',
    ],
    'Salaries': [
        # Employee salary payments
        'sanjeet kanojiya', 'sanjeetkanojia', 'salary payment', 
        'employee salary', 'staff payment', 'wages'
    ],
    'Miscellaneous': []  # Default catch-all
}

# =======================
# CATEGORIZATION RULES - INCOME (CREDITS)
# =======================
INCOME_CATEGORY_RULES = {
    'Salary': [
        'eightfold ai', 'gatewai integ', 'salary', 'salary credit', 'credited salary',
        'credited sal', 'sal credit', 'income', 'payroll', 'sal ', 'monthly salary',
        'net salary', 'salary transfer', 'emoluments'
    ],
    'Dividends': [
        # ACH Credit patterns for dividends (from actual transactions)
        'r:ach c-\s*(vedanta|wipro|ircon|jubilant|oil and natural gas|pcbl|rec)\s*(limited|ingrevia)?',
        'r:(apcotex|sansera engine)\s*(ind\s*)?div',
        # Generic dividend keywords
        'ach c-', 'dividend', 'vedanta', 'dividend credit', 'sansera',
        'div ', 'dividend paid', 'int div'
    ],
    'Interest': [
        # Specific interest credit patterns
        'credit interest', 'int.pd', 'nfl ncd iii-repay', 'nfl ncd', 'ach c- sbicard int',
        # Generic interest keywords
        'interest paid', 'int.paid', 'interest credit', 'interest earned',
        'savings interest', 'fd interest', 'int credit'
    ],
    'Cashbacks & Rewards': [
        'r:(npci\s*)?bhim\s*(-)?cashback', 'cashback',
        'cash back',           # two-word variant from CC statements
        'global value',        # HDFC SmartBuy/Global Value cashback program
        'reward', 'petro surcharge waiver', 'waiver', 'points credit',
        'surcharge waiver', 'consolidated fcy markup',  # forex markup refunds from CC
    ],
    'Refunds & Reversals': [
        'refund', 'reversal', 'reversed', 'return', 'chargeback',
        'cancellation', 'cancelled', 'credit reversal', 'tds refund',
        'income tax refund', 'yeida refund', 'yeida rps',
        # Merchant refunds — credits from these merchants = refund/return
        'amazon', 'blinkit', 'swiggy', 'zomato', 'eternal',
        'freshtohome', 'fresh to home', 'fittr',
        'myntra', 'pharmeasy', 'tata 1mg', '1mg',
        'enterprise rent', 'enterprise rent a car',
        'virgin atlantic',   # flight refund/compensation
        'titan',             # watch/jewellery return
        'konfhub',           # conference refund
        'razorpay licious',  # licious food refund
        # Ride-share credits (referral/promo credits)
        'ola', 'uber',
        # Insurance claim credits
        'icici lombard', 'imagine healthfin', 'hdfc ergo',
        # Bill payment reversals
        'bbps payment received',
        # UPI return
        'upiret',
        # Netbanking inward transfer credit
        'netbanking transfer',
    ],
    'Rent Received': [
        'pramod baghel', 'pramodbaghel', 'rent received', 'rental income'
    ],
    'Forex': [
        # Forex incoming credits (foreign exchange receipts)
        'imps-500616750132-airwallex', 'imps-502019675057-airwallex',
        'imps-502721772951-airwallex', 'imps-503422989394-airwallex',
        'imps-504806859272-airwallex',
        'airwallex hong kong', 'imps-airwallex',
        'bookmyforex', 'book my forex', 'razpbookmyforex',
        'foreign exchange', 'forex', 'currency exchange',
        'airwallex',
        'inw ',    # INW = International Wire — incoming forex credit from HDFC/ICICI
        'fcy markup',   # FCY markup refund credited to account
    ],
    'Transfers': [
        'neft cr-', 'imps cr-', 'rtgs cr-', 'upi cr-', 'fund transfer',
        'neft-', 'rtgs-', 'upi-', 'transfer credit',
        'netbanking transfer',
        'upiret',
        # Note: imps- removed to avoid matching airwallex forex transactions
    ],
    'Miscellaneous': []  # Default catch-all
}

# Keep backward compatibility
CATEGORY_RULES = EXPENSE_CATEGORY_RULES


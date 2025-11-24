from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, update
from backend.app.db.session import get_session
from backend.app.db.models import User
from backend.app.core.security import get_current_user

router = APIRouter(tags=["legal"])

# Comprehensive Terms and Conditions
TERMS_AND_CONDITIONS = """
VyRaTrader Terms and Conditions
Last Updated: December 2024

1. ACCEPTANCE OF TERMS
By accessing or using VyRaTrader (the "Platform"), you agree to be bound by these Terms and Conditions. If you do not agree to these terms, you may not use the Platform.

2. DEFINITIONS
2.1. "Platform" refers to VyRaTrader, an AI-powered trading platform
2.2. "User," "you," or "your" refers to anyone accessing the Platform
2.3. "Prince AI" or "AI" refers to the artificial intelligence system that generates trading signals and recommendations
2.4. "Service" refers to all services, features, and functionality provided by the Platform

3. ELIGIBILITY
3.1. You must be at least 18 years of age to use the Platform
3.2. You must have the legal capacity to enter into binding agreements in your jurisdiction
3.3. You may not use the Platform if it is illegal or prohibited in your jurisdiction
3.4. You agree to provide accurate, current, and complete information during registration

4. ACCOUNT REGISTRATION AND SECURITY
4.1. You are responsible for maintaining the confidentiality of your account credentials
4.2. You agree to notify us immediately of any unauthorized access to your account
4.3. You are responsible for all activities that occur under your account
4.4. We reserve the right to suspend or terminate accounts that violate these terms

5. AI TRADING DISCLAIMER
5.1. Prince AI is an artificial intelligence system that provides trading signals and recommendations
5.2. The AI's recommendations are based on algorithmic analysis and are NOT financial advice
5.3. Past performance does NOT guarantee future results
5.4. All trading decisions are made at your own risk and discretion
5.5. You acknowledge that AI predictions may be incorrect and result in losses
5.6. The AI uses market data from multiple sources; delays or errors may occur
5.7. We do NOT guarantee that the AI will always provide accurate signals

6. TRADING RISKS AND LIABILITIES
6.1. Trading involves substantial risk of loss and is not suitable for all investors
6.2. You may lose all or a portion of your invested capital
6.3. Past performance is not indicative of future results
6.4. Market volatility can cause sudden and significant losses
6.5. The value of investments can go down as well as up
6.6. We are NOT responsible for your trading losses
6.7. You should only trade with funds you can afford to lose

7. DEPOSITS AND WITHDRAWALS
7.1. Minimum deposit: GHS 500 or equivalent in other currencies
7.2. Deposit fee: 2% of the deposit amount
7.3. Withdrawal fee: 5% of the withdrawal amount
7.4. We reserve the right to verify your identity before processing withdrawals
7.5. Withdrawals may take 1-5 business days to process
7.6. You may be required to provide additional documentation for large withdrawals
7.7. We use third-party payment processors (Hubtel, Paystack, etc.) - their terms apply

8. FEES AND CHARGES
8.1. All fees are disclosed at the time of deposit or withdrawal
8.2. Fees may vary by payment method
8.3. Third-party payment processor fees are separate and may apply
8.4. We reserve the right to update fees with 30 days' notice

9. STOP-LOSS AND RISK MANAGEMENT
9.1. The Platform provides risk management tools (stop-loss, take-profit)
9.2. Low-risk profile: up to 3% stop-loss, 25% max exposure to volatile assets
9.3. Medium-risk profile: up to 7% stop-loss, 25% max exposure to volatile assets
9.4. High-risk profile: up to 15% stop-loss, 60% max exposure to volatile assets
9.5. You can adjust your risk profile in settings
9.6. We do NOT guarantee that stop-loss orders will execute at your specified price

10. INTELLECTUAL PROPERTY
10.1. All content on the Platform is owned by VyRaTrader or its licensors
10.2. The AI algorithms, strategies, and Prince AI are proprietary intellectual property
10.3. You may NOT copy, reproduce, or reverse-engineer any part of the Platform
10.4. You may NOT use the Platform to create competing services

11. PRIVACY AND DATA
11.1. Your use of the Platform is also governed by our Privacy Policy
11.2. We collect and use your data as described in the Privacy Policy
11.3. We use your trading data to improve AI models
11.4. You have the right to request deletion of your data (subject to legal requirements)
11.5. We implement industry-standard security measures to protect your data

12. USER CONDUCT
12.1. You agree to use the Platform only for lawful purposes
12.2. You may NOT use the Platform for money laundering or illegal activities
12.3. You may NOT attempt to manipulate markets or engage in fraudulent activities
12.4. You may NOT share your account with others
12.5. You may NOT use automated systems to exploit the Platform

13. API AND DATA USAGE
13.1. The Platform uses multiple third-party APIs for market data
13.2. API rate limits may affect data availability
13.3. If data is unavailable, Prince AI will inform you and suggest alternatives
13.4. We cache API responses to reduce consumption and costs
13.5. You understand that data delays may occur

14. LIMITATION OF LIABILITY
14.1. TO THE MAXIMUM EXTENT PERMITTED BY LAW, VYRATRADER SHALL NOT BE LIABLE FOR:
    a. Any losses resulting from trading decisions
    b. AI prediction errors or inaccuracies
    c. Data delays, errors, or unavailability
    d. Technical failures or interruptions
    e. Unauthorized access to accounts
    f. Third-party service failures
14.2. Our total liability shall not exceed the amount you paid in fees in the last 12 months
14.3. We do NOT guarantee uninterrupted or error-free service

15. INDEMNIFICATION
15.1. You agree to indemnify and hold harmless VyRaTrader, its officers, employees, and agents
15.2. This includes all claims, losses, damages, liabilities, costs, and expenses
15.3. This applies to any breach of these terms by you

16. TERMINATION
16.1. We may suspend or terminate your account for:
    a. Violation of these terms
    b. Suspected fraudulent activity
    c. Regulatory compliance requirements
    d. Any reason we deem necessary
16.2. You may close your account at any time
16.3. Upon termination, you are entitled to your remaining balance (minus fees)
16.4. We may retain your data for 90 days after account closure for legal compliance

17. DISPUTES AND GOVERNING LAW
17.1. These terms are governed by the laws of Ghana
17.2. Any disputes shall be resolved through arbitration in Accra, Ghana
17.3. Class action lawsuits are waived to the extent permitted by law

18. CHANGES TO TERMS
18.1. We may update these terms at any time
18.2. You will be notified of material changes via email or Platform notification
18.3. Continued use of the Platform after changes constitutes acceptance
18.4. We recommend reviewing terms periodically

19. THIRD-PARTY SERVICES
19.1. The Platform integrates with:
    a. Payment processors (Hubtel, Paystack, Stripe)
    b. Trading exchanges (Binance, OANDA)
    c. Market data providers (CoinGecko, Alpha Vantage, etc.)
    d. AI providers (OpenAI, etc.)
19.2. Third-party terms apply to their respective services
19.3. We are not responsible for third-party service failures

20. RELIABLE SIGNALS AND WAIT PERIODS
20.1. Prince AI provides signals based on available market data
20.2. If market data is unavailable due to API limits, Prince AI will inform you
20.3. You may need to wait until the next day for updated data
20.4. Prince AI may suggest alternative markets (forex) during unavailability
20.5. Cached data may be used if available and recent (less than 5 minutes old)
20.6. We do NOT guarantee data availability at all times

21. NOTIFICATIONS
21.1. Prince AI may send push notifications when reliable signals are detected
21.2. You can opt-out of notifications in settings
21.3. Notifications expire after a certain time (typically 1-4 hours)
21.4. You are responsible for acting on signals promptly

22. RISK MANAGEMENT AND STOP LOSS
22.1. All trades are subject to risk management rules based on your risk profile
22.2. Prince AI recommends stop-loss levels, but you can override them
22.3. We strongly recommend using stop-loss orders to limit losses
22.4. Dynamic position sizing is applied based on market volatility

23. SUPPORT AND HELP
23.1. For support, contact us at support@vyratrader.com
23.2. We aim to respond within 24-48 hours
23.3. Prince AI can help answer questions within the Platform

24. KYC AND COMPLIANCE
24.1. We are committed to Know Your Customer (KYC) compliance
24.2. We may request additional documentation to verify your identity
24.3. We comply with anti-money laundering (AML) regulations
24.4. We may freeze accounts pending investigation if suspicious activity is detected

25. FORCE MAJEURE
25.1. We are not liable for delays or failures due to circumstances beyond our control
25.2. This includes but is not limited to: natural disasters, war, pandemic, cyber attacks, etc.

26. ENTIRE AGREEMENT
26.1. These terms constitute the entire agreement between you and VyRaTrader
26.2. Any previous oral or written agreements are superseded

27. SEVERABILITY
27.1. If any provision is deemed invalid, the remainder of terms remains in effect

28. NO WAIVER
28.1. Our failure to enforce a term does not constitute a waiver of our rights

29. CONTACT INFORMATION
If you have questions about these terms, contact us at:
Email: legal@vyratrader.com
Address: Accra, Ghana

By using VyRaTrader, you acknowledge that you have read, understood, and agree to be bound by these Terms and Conditions.
"""

PRIVACY_POLICY = """
VyRaTrader Privacy Policy
Last Updated: December 2024

1. INFORMATION WE COLLECT
1.1. Personal Information: Name, email, phone, address, date of birth
1.2. Financial Data: Account balances, transactions, trading history, deposits, withdrawals
1.3. Usage Data: App interactions, AI chat logs, feature usage, screen views
1.4. Device Information: IP address, device type, operating system, unique identifiers
1.5. Market Data: Your trade preferences, signals generated for you, portfolio composition

2. HOW WE USE YOUR DATA
2.1. Provide Services: Process trades, manage accounts, execute orders
2.2. Improve AI: Train Prince AI using aggregated, anonymized trading data
2.3. Personalize Experience: Customize signals and recommendations for you
2.4. Communicate: Send updates, notifications, alerts, marketing (with consent)
2.5. Security: Detect fraud, prevent abuse, verify identity
2.6. Compliance: Meet legal obligations, KYC requirements, AML checks
2.7. Analytics: Analyze usage patterns to improve the Platform

3. DATA SHARING
3.1. We share data with:
    a. Payment processors (Hubtel, Paystack) for transactions
    b. Trading exchanges (Binance, OANDA) for order execution
    c. Market data providers for real-time prices
    d. Cloud service providers for hosting
    e. Analytics services (anonymized)
3.2. We do NOT sell your personal data to third parties
3.3. We may share data if required by law or to protect our rights

4. DATA SECURITY
4.1. We use industry-standard encryption (SSL/TLS) for data in transit
4.2. Sensitive data is encrypted at rest
4.3. Access controls limit who can view your data
4.4. Payment information is tokenized and never stored directly
4.5. We conduct regular security audits

5. YOUR RIGHTS
5.1. Access: Request a copy of your data
5.2. Correction: Update incorrect information
5.3. Deletion: Request deletion (subject to legal requirements)
5.4. Portability: Export your data in a machine-readable format
5.5. Opt-out: Unsubscribe from marketing communications
5.6. Objection: Object to certain data processing

6. DATA RETENTION
6.1. We retain data while your account is active
6.2. After account closure: 90 days for legal compliance, then deletion
6.3. Trading data may be kept longer for analytics (anonymized)

7. COOKIES AND TRACKING
7.1. We use cookies and similar technologies for:
    a. Authentication
    b. Preferences
    c. Analytics
    d. Security
7.2. You can manage cookies in your browser settings

8. AI AND MACHINE LEARNING
8.1. Your trading data (anonymized) helps train Prince AI
8.2. This helps improve AI predictions for all users
8.3. Your individual identity is not revealed to other users
8.4. We may use third-party AI services (OpenAI, etc.) - their privacy policies apply

9. INTERNATIONAL USERS
9.1. We comply with GDPR for EU users
9.2. Data is primarily stored in Ghana
9.3. Some data may be processed in other countries for service delivery

10. CHILDREN'S PRIVACY
10.1. We do not knowingly collect data from children under 18
10.2. If you believe we have, contact us to have it removed

11. CHANGES TO THIS POLICY
11.1. We may update this policy periodically
11.2. You will be notified of material changes
11.3. Continued use constitutes acceptance

12. CONTACT US
For privacy concerns, contact: privacy@vyratrader.com
"""

@router.get("/legal/terms")
async def get_terms():
    return {"terms": TERMS_AND_CONDITIONS}

@router.get("/legal/privacy")
async def get_privacy():
    return {"privacy_policy": PRIVACY_POLICY}

@router.post("/legal/accept")
async def accept_terms(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    stmt = update(User).where(User.id == current_user.id).values(accepted_terms=True)
    await session.execute(stmt)
    await session.commit()
    return {"status": "accepted"}

// lib/main.dart
import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:provider/provider.dart';

import 'core/theme.dart';
import 'core/api_client.dart';
import 'core/connectivity_diagnostic.dart';
import 'core/secure_storage.dart';
import 'providers/auth_provider.dart';
import 'providers/trades_provider.dart';
import 'providers/payments_provider.dart';
import 'routes/app_routes.dart';
import 'widgets/prince_floating_assistant.dart';
import 'widgets/splash.dart';
import 'core/security/security_manager.dart';
import 'services/ad_manager.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  debugPrint('🏁 Flutter binding initialized');

  // Initialize Google Mobile Ads
  try {
    await AdManager.instance.initialize();
    debugPrint('✅ Google Mobile Ads initialized');
  } catch (e) {
    debugPrint('⚠️ Ad initialization failed (continuing anyway): $e');
  }

  // 1) Load .env first (we assume you've added ".env" to flutter assets)
  try {
    await dotenv.load(fileName: '.env');
    debugPrint('✅ .env loaded: ${dotenv.env['API_BASE_URL']}');
  } catch (e) {
    // If loading fails (shouldn't if .env is added to assets), set fallback values.
    debugPrint(
        '⚠️ dotenv.load() failed: $e — using fallback values for web/CI');
    // Provide a minimal fallback so code that reads dotenv.env won't crash.
    dotenv.env['API_BASE_URL'] = 'https://vyratrader.onrender.com';
  }

  // 2) Initialize security AFTER dotenv is ready.
  try {
    await SecurityManager().initialize();
    debugPrint('✅ SecurityManager initialized');
  } catch (e, s) {
    debugPrint('❌ SecurityManager.initialize() failed: $e\n$s');
    // Decide: continue or rethrow. We'll continue but SecurityManager may be limited on web.
  }

  // 3) Build ApiClient using env (safe now because dotenv.env is initialized)
  final envUrl = dotenv.env['API_BASE_URL'];
  final apiBase = envUrl != null && envUrl.isNotEmpty 
      ? (envUrl.endsWith('/api/v1') ? envUrl : '$envUrl/api/v1')
      : 'https://vyratrader.onrender.com/api/v1';
  final api = ApiClient(baseUrl: apiBase);
  debugPrint('✅ ApiClient created with base: $apiBase');

  // 4) Run connectivity diagnostic
  try {
    debugPrint('🔍 Running connectivity diagnostic...');
    final results = await ConnectivityDiagnostic.testAllEndpoints(api);
    ConnectivityDiagnostic.printDiagnosticResults(results);
  } catch (e) {
    debugPrint('⚠️ Connectivity diagnostic failed: $e');
  }

  // 5) Run app
  runApp(MyApp(api: api));
}

class MyApp extends StatelessWidget {
  final ApiClient api;

  const MyApp({super.key, required this.api});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        Provider<ApiClient>.value(value: api),
        ChangeNotifierProvider(create: (_) => AuthProvider(api: api)),
        ChangeNotifierProvider(create: (_) => TradesProvider(api: api)),
        ChangeNotifierProvider(create: (_) => PaymentsProvider(api: api)),
      ],
      child: Consumer<AuthProvider>(
        builder: (context, auth, _) {
          return MaterialApp(
            debugShowCheckedModeBanner: false,
            title: 'VyRaTrader',
            theme: VyRaTheme.darkTheme,
            initialRoute: '/splash',
            routes: {
              '/splash': (context) => SplashScreen(api: api),
              ...AppRoutes.routes,
            },
            builder: (context, child) {
              return PrinceFloatingAssistant(
                userId: auth.user?.id,
                autoOpenOnLaunch: false, // Set to true if you want auto-open on first launch
                child: child ?? const SizedBox(),
              );
            },
          );
        },
      ),
    );
  }
}

class SplashScreen extends StatefulWidget {
  final ApiClient api;
  
  const SplashScreen({super.key, required this.api});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _checkAuthAndNavigate();
  }

  Future<void> _checkAuthAndNavigate() async {
    await Future.delayed(const Duration(seconds: 5));
    
    if (!mounted) return;
    
    final auth = Provider.of<AuthProvider>(context, listen: false);
    
    // Check if user has valid token by checking secure storage
    try {
      final token = await SecureStorage.getAccessToken();
      
      if (token != null && token.isNotEmpty) {
        // User is authenticated, go to Main screen
        Navigator.pushReplacementNamed(context, AppRoutes.main);
      } else {
        // User not authenticated, go to Onboarding
        Navigator.pushReplacementNamed(context, AppRoutes.onboarding);
      }
    } catch (e) {
      // If any error, go to onboarding
      Navigator.pushReplacementNamed(context, AppRoutes.onboarding);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Splash(
      onDone: () {
        // This will be called after splash animation completes
        _checkAuthAndNavigate();
      },
    );
  }
}

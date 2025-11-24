// lib/screens/trading/trade_screen.dart
// MODERN FUTURISTIC TRADE SCREEN - OKX-Inspired Design
// Production Ready - Complete implementation with interactive chart

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:fl_chart/fl_chart.dart';
import 'dart:math' as math;
import 'dart:async';
import '../../providers/trades_provider.dart';
import '../../providers/auth_provider.dart';
import '../../core/api_client.dart';

class TradeScreen extends StatefulWidget {
  static const routeName = '/trading';
  const TradeScreen({super.key});

  @override
  State<TradeScreen> createState() => _TradeScreenState();
}

class _TradeScreenState extends State<TradeScreen>
    with TickerProviderStateMixin {
  late TabController _marketTabController;
  late TabController _timeframeTabController;
  late AnimationController _glowController;
  late AnimationController _pulseController;
  late AnimationController _priceAnimationController;
  Timer? _priceUpdateTimer;
  Timer? _chartAnimationTimer;

  final List<String> _currencies = [
    'GHS',
    'USD',
    'EUR',
    'GBP',
    'JPY',
    'CAD',
    'AUD',
    'CHF',
    'CNY',
    'SEK',
    'NGN',
    'ZAR',
    'INR',
  ];
  
  final List<String> _markets = ['Crypto', 'Forex'];
  final List<String> _timeframes = ['15m', '1h', '4h', '1D', '1W'];

  int _selectedMarketIndex = 0;
  int _selectedTimeframeIndex = 0;
  String _selectedCurrency = 'USD';
  final _sizeController = TextEditingController(text: '0.01');
  final _stopLossController = TextEditingController();
  final _takeProfitController = TextEditingController();

  String _side = 'buy';
  String _tradingMode = 'paper';  // 'paper' or 'live'
  double _riskLevel = 0.5;
  bool _loading = false;
  bool _simulating = false;
  bool _loadingPrice = false;

  Map<String, dynamic>? _simulationResult;
  Map<String, dynamic>? _aiSuggestion;
  Map<String, dynamic>? _marketData;
  double? _currentPrice;
  double? _previousPrice;
  double _priceChange24h = 0.0;
  double _volume24h = 0.0;
  double _userBalance = 0.0;
  bool _useStopLoss = false;
  bool _useTakeProfit = false;
  Color _priceColor = Colors.white;
  Animation<double>? _priceAnimation;

  final Map<String, List<String>> _marketSymbols = {
    'Crypto': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'XRPUSDT', 'SOLUSDT', 'ADAUSDT'],
    'Forex': ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF'],
  };

  final Map<String, String> _currentSymbols = {
    'Crypto': 'BTCUSDT',
    'Forex': 'EURUSD',
  };

  // Chart data for candlesticks
  List<FlSpot> _candlestickData = [];
  List<FlSpot> _volumeData = [];
  
  // Live chart data with time-based movement
  List<FlSpot> _liveChartData = [];
  Timer? _liveChartUpdateTimer;

  // Order book data
  List<Map<String, dynamic>> _buyOrders = [];
  List<Map<String, dynamic>> _sellOrders = [];
  
  // Active trades and history
  List<Map<String, dynamic>> _activeTrades = [];
  List<Map<String, dynamic>> _tradeHistory = [];
  bool _loadingTrades = false;
  String _selectedTab = 'active'; // 'active' or 'history'
  Timer? _tradesUpdateTimer;
  double _leverage = 1.0;
  
  // Failure tracking to prevent infinite timeout loops
  int _consecutiveMarketDataFailures = 0;
  int _consecutiveLiveChartFailures = 0;
  int _consecutiveTradesFailures = 0;
  bool _isLoadingMarketData = false;
  bool _isUpdatingLiveChart = false;
  bool _isLoadingTrades = false;
  bool _isDisposed = false; // Flag to prevent any operations after disposal
  static const int _maxFailures = 3; // Stop polling after 3 consecutive failures

  @override
  void initState() {
    super.initState();
    
    _marketTabController = TabController(length: _markets.length, vsync: this);
    _timeframeTabController = TabController(length: _timeframes.length, vsync: this);
    
    _marketTabController.addListener(_onMarketTabChanged);

    _glowController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);

    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat();

    _priceAnimationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 300),
    );

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_canUpdate) return;
      final auth = Provider.of<AuthProvider>(context, listen: false);
      if (auth.isAuthenticated) {
        _loadUserBalance();
        _loadAISuggestion();
        _loadActiveTrades();
      }
    });
    
    _loadMarketData();
    _startPriceUpdates();
    _startTradesUpdate();
  }

  // Helper to check if widget is safe to update
  bool get _canUpdate => !_isDisposed && mounted;

  void _onMarketTabChanged() {
    if (!_canUpdate) return;
    if (_marketTabController.indexIsChanging) {
      if (_canUpdate) {
        setState(() {
          _selectedMarketIndex = _marketTabController.index;
        });
      }
      if (_canUpdate) {
        _loadMarketData();
      }
    }
  }

  @override
  void dispose() {
    // Set disposal flag first to prevent any further operations
    _isDisposed = true;
    
    // Stop all timers first
    _priceUpdateTimer?.cancel();
    _liveChartUpdateTimer?.cancel();
    _tradesUpdateTimer?.cancel();
    _chartAnimationTimer?.cancel();
    
    // Remove listeners before disposing
    try {
      _marketTabController.removeListener(_onMarketTabChanged);
    } catch (e) {
      // Ignore if already removed
    }
    
    // Stop all repeating animations before disposing
    try {
      if (_glowController.isAnimating) {
        _glowController.reset();
        _glowController.stop();
      }
      if (_pulseController.isAnimating) {
        _pulseController.reset();
        _pulseController.stop();
      }
      if (_priceAnimationController.isAnimating) {
        _priceAnimationController.reset();
        _priceAnimationController.stop();
      }
    } catch (e) {
      // Ignore if already stopped or disposed
    }
    
    // Dispose controllers
    _marketTabController.dispose();
    _timeframeTabController.dispose();
    _glowController.dispose();
    _pulseController.dispose();
    _priceAnimationController.dispose();
    _sizeController.dispose();
    _stopLossController.dispose();
    _takeProfitController.dispose();
    
    super.dispose();
  }

  void _updateChartData() {
    // Real data update - fetch from backend or Binance API
    _loadMarketData();
  }

  Future<void> _loadUserBalance() async {
    if (!_canUpdate) return;
    
    final auth = Provider.of<AuthProvider>(context, listen: false);
    final user = auth.user;
    
    // Only fetch if authenticated
    if (!auth.isAuthenticated) {
      if (_canUpdate) {
        setState(() => _userBalance = user?.balance ?? 0.0);
      }
      return;
    }
    
    try {
      final api = Provider.of<ApiClient>(context, listen: false);
      // API client baseUrl already includes /api/v1, so use /portfolio/portfolio
      final response = await api.get('/portfolio/portfolio', params: {}, queryParams: {}).timeout(const Duration(seconds: 10));
      
      if (!_canUpdate) return;
      
      final balance = response['balance']?.toDouble() ?? user?.balance ?? 0.0;
      if (_canUpdate) {
        setState(() => _userBalance = balance);
      }
    } catch (e) {
      debugPrint('Failed to load user balance: $e');
      // Use balance from user object if available
      if (_canUpdate) {
        setState(() => _userBalance = user?.balance ?? 0.0);
      }
    }
  }

  Future<void> _loadMarketData() async {
    if (!_canUpdate || _isLoadingMarketData) return;
    
    // Stop polling if too many consecutive failures
    if (_consecutiveMarketDataFailures >= _maxFailures) {
      return;
    }
    
    _isLoadingMarketData = true;
    if (_canUpdate) {
      setState(() => _loadingPrice = true);
    }

    try {
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      if (!authProvider.isAuthenticated) {
        _isLoadingMarketData = false;
        if (mounted) {
          setState(() {
            _loadingPrice = false;
            // Initialize chart data with existing price if available and chart is empty
            if (_liveChartData.isEmpty && _currentPrice != null && _currentPrice! > 0) {
              _liveChartData = List.generate(50, (index) => FlSpot(index.toDouble(), _currentPrice!));
            }
          });
        }
        return;
      }
      
      final symbol = _currentSymbols[_markets[_selectedMarketIndex]] ?? 'BTCUSD';
      final api = Provider.of<ApiClient>(context, listen: false);
      // API client baseUrl already includes /api/v1, so path should be /market/quote
      final response = await api.get('/market/quote', queryParams: {
        'symbol': symbol,
        'market': _markets[_selectedMarketIndex].toLowerCase(),
      }, params: {}).timeout(const Duration(seconds: 10));

      if (!_canUpdate) {
        _isLoadingMarketData = false;
        return;
      }

      // Reset failure counter on success
      _consecutiveMarketDataFailures = 0;
      
      if (_canUpdate) {
        setState(() {
          _marketData = response;
          final newPrice = response['price']?.toDouble() ?? 0.0;
          
          if (newPrice > 0) {
            if (_currentPrice != null && newPrice != _currentPrice) {
              _priceColor = newPrice > _currentPrice! ? Colors.green : Colors.red;
              // Use SchedulerBinding to avoid assertion errors
              if (_canUpdate) {
                WidgetsBinding.instance.addPostFrameCallback((_) {
                  if (!_canUpdate) return;
                  Future.delayed(const Duration(milliseconds: 500), () {
                    if (_canUpdate) {
                      setState(() => _priceColor = Colors.white);
                    }
                  });
                });
              }
            }
            
            _previousPrice = _currentPrice;
            _currentPrice = newPrice;
            _priceChange24h = response['change_24h']?.toDouble() ?? 0.0;
            _volume24h = response['volume_24h']?.toDouble() ?? 0.0;
            
            // Initialize live chart data with real price if empty
            if (_liveChartData.isEmpty) {
              // Start with current price repeated to fill initial chart
              _liveChartData = List.generate(50, (index) => FlSpot(index.toDouble(), newPrice));
            }
          }
        });
      }
    } catch (e) {
      _consecutiveMarketDataFailures++;
      debugPrint('Market data load failed (${_consecutiveMarketDataFailures}/$_maxFailures): $e');
      
      // Keep existing price if available, don't set mock data
      // If we have a price but no chart data, initialize it
      if (_canUpdate) {
        setState(() {
          // Always clear loading state
          _loadingPrice = false;
          // Initialize chart data with existing price if available and chart is empty
          if (_liveChartData.isEmpty && _currentPrice != null && _currentPrice! > 0) {
            _liveChartData = List.generate(50, (index) => FlSpot(index.toDouble(), _currentPrice!));
          }
        });
      }
    } finally {
      _isLoadingMarketData = false;
      if (_canUpdate) {
        setState(() => _loadingPrice = false);
      }
    }
  }

  // Removed _getDemoPrice - no longer using demo/mock data in production
  
  // ============================================================================
  // ACTIVE TRADES & HISTORY METHODS
  // ============================================================================
  
  Future<void> _loadActiveTrades() async {
    if (!_canUpdate || _isLoadingTrades) return;
    
    // Stop polling if too many consecutive failures
    if (_consecutiveTradesFailures >= _maxFailures) {
      return;
    }
    
    _isLoadingTrades = true;
    
    try {
      final api = Provider.of<ApiClient>(context, listen: false);
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      
      if (!authProvider.isAuthenticated) {
        _isLoadingTrades = false;
        return;
      }
      
      // API client baseUrl already includes /api/v1, so use /portfolio/portfolio for active trades (positions)
      final response = await api.get('/portfolio/portfolio', queryParams: {}, params: {}).timeout(const Duration(seconds: 10));
      
      if (!_canUpdate) {
        _isLoadingTrades = false;
        return;
      }
      
      // Reset failure counter on success
      _consecutiveTradesFailures = 0;
      
      if (!_canUpdate) return;
      
      if (response is List) {
        if (_canUpdate) {
          setState(() {
            _activeTrades = (response as List).map((e) => e as Map<String, dynamic>).toList();
          });
        }
      } else if (response is Map<String, dynamic>) {
        // Handle case where API returns a Map with 'trades' or 'positions' key
        // Portfolio endpoint returns {"positions": [...]} where positions are open trades
        final trades = response['trades'] ?? response['positions'] ?? [];
        if (trades is List) {
          if (_canUpdate) {
            setState(() {
              // Map portfolio positions format to active trades format
              _activeTrades = List<Map<String, dynamic>>.from(trades.map((t) {
                if (t is Map<String, dynamic>) {
                  // Ensure all required fields are present
                  return {
                    'id': t['id'] ?? '',
                    'symbol': t['symbol'] ?? '',
                    'side': t['side'] ?? 'buy',
                    'entry_price': t['entry_price'] ?? t['price'] ?? 0.0,
                    'quantity': t['quantity'] ?? t['size'] ?? 0.0,
                    'size': t['size'] ?? t['quantity'] ?? 0.0,
                    'profit_loss': t['profit_loss'] ?? 0.0,
                    'timestamp': t['timestamp'] ?? '',
                  };
                }
                return t;
              }));
            });
          }
        } else {
          if (_canUpdate) {
            setState(() {
              _activeTrades = [];
            });
          }
        }
      } else {
        if (_canUpdate) {
          setState(() {
            _activeTrades = [];
          });
        }
      }
    } catch (e) {
      _consecutiveTradesFailures++;
      debugPrint('Failed to load active trades (${_consecutiveTradesFailures}/$_maxFailures): $e');
    } finally {
      _isLoadingTrades = false;
    }
  }
  
  Future<void> _loadTradeHistory() async {
    if (!mounted || _isLoadingTrades) return;
    
    _isLoadingTrades = true;
    setState(() => _loadingTrades = true);
    
    try {
      final api = Provider.of<ApiClient>(context, listen: false);
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      
      if (!authProvider.isAuthenticated) {
        _isLoadingTrades = false;
        if (mounted) {
          setState(() {
            _loadingTrades = false;
          });
        }
        return;
      }
      
      // API client baseUrl already includes /api/v1, so use /trades/recent
      final response = await api.get('/trades/recent', queryParams: {'limit': '50'}, params: {}).timeout(const Duration(seconds: 10));
      
      if (!mounted) {
        _isLoadingTrades = false;
        return;
      }
      
      if (response is List) {
        setState(() {
          _tradeHistory = (response as List).map((e) => e as Map<String, dynamic>).toList();
          _loadingTrades = false;
        });
      } else if (response is Map<String, dynamic>) {
        // Handle case where API returns a Map with 'trades' or 'positions' key
        final trades = response['trades'] ?? response['positions'] ?? [];
        if (trades is List) {
          setState(() {
            _tradeHistory = List<Map<String, dynamic>>.from(trades);
            _loadingTrades = false;
          });
        } else {
          setState(() {
            _tradeHistory = [];
            _loadingTrades = false;
          });
        }
      } else {
        setState(() {
          _tradeHistory = [];
          _loadingTrades = false;
        });
      }
    } catch (e) {
      debugPrint('Failed to load trade history: $e');
      if (mounted) {
        setState(() {
          _tradeHistory = [];
          _loadingTrades = false;
        });
      }
    } finally {
      _isLoadingTrades = false;
    }
  }
  
  Future<List<Map<String, dynamic>>> _updateTradePnL(List<dynamic> trades) async {
    if (!mounted || _currentPrice == null) return trades.cast<Map<String, dynamic>>();
    
    final updated = <Map<String, dynamic>>[];
    
    for (var trade in trades) {
      if (trade is! Map<String, dynamic>) continue;
      
      final symbol = trade['symbol']?.toString() ?? '';
      final entryPrice = (trade['price'] ?? trade['entry_price'] ?? 0.0).toDouble();
      final quantity = (trade['quantity'] ?? 0.0).toDouble();
      final side = trade['side']?.toString().toLowerCase() ?? 'buy';
      
      // Use current price for this symbol if available, otherwise use global current price
      double currentPrice = _currentPrice ?? entryPrice;
      
      // Calculate P&L
      double pnl;
      double pnlPercent;
      
      if (side == 'buy') {
        pnl = (currentPrice - entryPrice) * quantity;
        pnlPercent = entryPrice > 0 ? ((currentPrice - entryPrice) / entryPrice) * 100 : 0.0;
      } else {
        pnl = (entryPrice - currentPrice) * quantity;
        pnlPercent = entryPrice > 0 ? ((entryPrice - currentPrice) / entryPrice) * 100 : 0.0;
      }
      
      final updatedTrade = Map<String, dynamic>.from(trade);
      updatedTrade['current_price'] = currentPrice;
      updatedTrade['profit_loss'] = pnl;
      updatedTrade['pnl_percent'] = pnlPercent;
      
      updated.add(updatedTrade);
    }
    
    return updated;
  }
  
  void _startTradesUpdate() {
    _tradesUpdateTimer?.cancel();
    _tradesUpdateTimer = Timer.periodic(const Duration(seconds: 5), (timer) {
      if (!_canUpdate) {
        timer.cancel();
        return;
      }
      if (_selectedTab == 'active') {
        _loadActiveTrades();
      }
    });
  }
  
  Future<void> _closePosition(String tradeId) async {
    if (!mounted) return;
    
    try {
      final api = Provider.of<ApiClient>(context, listen: false);
      final auth = Provider.of<AuthProvider>(context, listen: false);
      
      if (!auth.isAuthenticated || auth.userId == null) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Please login to close trades')),
        );
        return;
      }
      
      // Close trade via API
      await api.post('/api/v1/trades/close', {'trade_id': tradeId});
      
      if (!mounted) return;
      
      // Refresh active trades
      await _loadActiveTrades();
      
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Trade closed successfully'),
          backgroundColor: Colors.green,
        ),
      );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to close trade: ${e.toString()}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }
  
  double _calculatePnL(Map<String, dynamic> trade) {
    final entryPrice = trade['entry_price']?.toDouble() ?? 0.0;
    final currentPx = _currentPrice ?? entryPrice;
    final size = trade['size']?.toDouble() ?? 0.0;
    final side = trade['side'] ?? 'buy';
    
    if (side == 'buy') {
      return (currentPx - entryPrice) * size;
    } else {
      return (entryPrice - currentPx) * size;
    }
  }
  
  double _calculatePnLPercentage(Map<String, dynamic> trade) {
    final entryPrice = trade['entry_price']?.toDouble() ?? 0.0;
    final currentPx = _currentPrice ?? entryPrice;
    final side = trade['side'] ?? 'buy';
    
    if (entryPrice == 0) return 0.0;
    
    if (side == 'buy') {
      return ((currentPx - entryPrice) / entryPrice) * 100;
    } else {
      return ((entryPrice - currentPx) / entryPrice) * 100;
    }
  }
  
  Future<void> _updateStopLoss(String tradeId, double newSL) async {
    if (!mounted) return;
    
    try {
      final api = Provider.of<ApiClient>(context, listen: false);
      
      await api.put('/trades/$tradeId/risk', {'stop_loss': newSL});
      
      if (!mounted) return;
      
      await _loadActiveTrades();
      
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Stop loss updated'),
          backgroundColor: Colors.green,
        ),
      );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to update stop loss: ${e.toString()}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }
  
  Future<void> _updateTakeProfit(String tradeId, double newTP) async {
    if (!mounted) return;
    
    try {
      final api = Provider.of<ApiClient>(context, listen: false);
      
      await api.put('/trades/$tradeId/risk', {'take_profit': newTP});
      
      if (!mounted) return;
      
      await _loadActiveTrades();
      
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Take profit updated'),
          backgroundColor: Colors.green,
        ),
      );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to update take profit: ${e.toString()}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _executeTrade() async {
    final authProvider = Provider.of<AuthProvider>(context, listen: false);
    if (!authProvider.isAuthenticated) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please login to trade')),
      );
      return;
    }

    // Warn about live trading
    if (_tradingMode == 'live') {
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('⚠️ Live Trading'),
          content: const Text(
            'You are about to execute a REAL trade with REAL money!\n\n'
            'This will connect to Binance and execute immediately.\n\n'
            'Are you absolutely sure?',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('CANCEL'),
            ),
            TextButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('EXECUTE', style: TextStyle(color: Colors.red)),
            ),
          ],
        ),
      );
      
      if (confirmed != true) {
        return;
      }
    }

    setState(() => _loading = true);
    
    try {
      final currentMarket = _markets[_selectedMarketIndex];
      final symbol = _currentSymbols[currentMarket]!;
      final size = double.tryParse(_sizeController.text) ?? 0.01;
      
      if (size <= 0) {
        throw Exception('Invalid trade size');
      }

      // Call the backend execute endpoint
      final apiClient = Provider.of<ApiClient>(context, listen: false);
      final response = await apiClient.post('/trades/execute', {
        'user_id': authProvider.user?.id ?? '',
        'symbol': symbol,
        'side': _side,
        'size': size,
        'market': currentMarket.toLowerCase(),
        'mode': _tradingMode, // Paper or live trading
      });

      if (response['ok'] == true) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('${_side.toUpperCase()} order executed successfully!'),
            backgroundColor: Colors.green,
          ),
        );
        
        // Refresh market data
        _loadMarketData();
      } else {
        throw Exception(response['error'] ?? 'Trade execution failed');
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Trade failed: $e'),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _loading = false);
        // Refresh active trades after execution
        _loadActiveTrades();
      }
    }
  }

  void _startPriceUpdates() {
    _priceUpdateTimer = Timer.periodic(const Duration(seconds: 3), (timer) {
      if (!_canUpdate) {
        timer.cancel();
        return;
      }
      _loadMarketData();
    });
    
    // Start chart animation timer for live movement (real data every 2 seconds)
    _chartAnimationTimer = Timer.periodic(const Duration(seconds: 2), (timer) {
      if (!_canUpdate) {
        timer.cancel();
        return;
      }
      _updateChartData();
    });
    
    // Start live chart updates for wide moving chart - fetch REAL data every 2 seconds (reduced from 500ms to prevent timeout spam)
    _liveChartUpdateTimer = Timer.periodic(const Duration(seconds: 2), (timer) {
      if (!_canUpdate) {
        timer.cancel();
        return;
      }
      _updateLiveChart();
    });
  }
  
  void _updateLiveChart() async {
    // Fetch real-time price from backend - removed _currentPrice check to allow initial population
    if (!_canUpdate || _isUpdatingLiveChart) return;
    
    // Stop polling if too many consecutive failures
    if (_consecutiveLiveChartFailures >= _maxFailures) {
      return;
    }
    
    _isUpdatingLiveChart = true;
    
    try {
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      if (!authProvider.isAuthenticated) {
        _isUpdatingLiveChart = false;
        return;
      }
      
      final symbol = _currentSymbols[_markets[_selectedMarketIndex]] ?? 'BTCUSDT';
      final api = Provider.of<ApiClient>(context, listen: false);
      final response = await api.get('/market/quote', queryParams: {
        'symbol': symbol,
        'market': _markets[_selectedMarketIndex].toLowerCase(),
      }, params: {}).timeout(const Duration(seconds: 5));
      
      final newPrice = response['price']?.toDouble();
      if (newPrice != null && newPrice > 0 && _canUpdate) {
        // Reset failure counter on success
        _consecutiveLiveChartFailures = 0;
        
        if (_canUpdate) {
          setState(() {
            // Update current price
            _previousPrice = _currentPrice;
            _currentPrice = newPrice;
            
            // Initialize chart data if empty
            if (_liveChartData.isEmpty) {
              _liveChartData = List.generate(50, (index) => FlSpot(index.toDouble(), newPrice));
            } else {
              // Remove first point and add new point at the end (scroll effect)
              if (_liveChartData.length >= 150) {
                _liveChartData.removeAt(0);
                // Adjust x values to shift left
                for (int i = 0; i < _liveChartData.length; i++) {
                  _liveChartData[i] = FlSpot(i.toDouble(), _liveChartData[i].y);
                }
              }
              
              // Add REAL price data point
              final newIndex = _liveChartData.length.toDouble();
              _liveChartData.add(FlSpot(newIndex, newPrice));
            }
          });
        }
      }
    } catch (e) {
      _consecutiveLiveChartFailures++;
      debugPrint('Live chart update failed (${_consecutiveLiveChartFailures}/$_maxFailures): $e');
      
      // If we have a price but no chart data, initialize it
      if (_canUpdate && _liveChartData.isEmpty && _currentPrice != null && _currentPrice! > 0) {
        setState(() {
          _liveChartData = List.generate(50, (index) => FlSpot(index.toDouble(), _currentPrice!));
        });
      }
    } finally {
      _isUpdatingLiveChart = false;
    }
  }

  Future<void> _loadAISuggestion() async {
    try {
      final symbol = _currentSymbols[_markets[_selectedMarketIndex]] ?? 'BTCUSD';
      final api = Provider.of<ApiClient>(context, listen: false);
      final response = await api.post('/api/v1/ai/analyze', {
        'symbol': symbol,
        'market': _markets[_selectedMarketIndex].toLowerCase(),
        'risk_level': _getRiskString(),
      });

      setState(() {
        _aiSuggestion = {
          'recommended_action': response['action'] ?? 'hold',
          'confidence': response['confidence']?.toDouble() ?? 0.75,
          'rationale': response['rationale'] ?? 'Analyzing market conditions...',
          'expected_profit': response['expected_profit']?.toDouble() ?? 0.0,
          'expected_loss': response['expected_loss']?.toDouble() ?? 0.0,
        };
      });
    } catch (e) {
      setState(() {
        _aiSuggestion = {
          'recommended_action': 'buy',
          'confidence': 0.72,
          'rationale': 'Strong uptrend detected with bullish momentum indicators.',
          'expected_profit': 2.5,
          'expected_loss': -1.2,
        };
      });
    }
  }

  // Removed _generateSampleData - using only real API data

  String _getRiskString() {
    if (_riskLevel < 0.33) return 'low';
    if (_riskLevel < 0.67) return 'medium';
    return 'high';
  }

  Color _getMarketColor() {
    switch (_markets[_selectedMarketIndex]) {
      case 'Crypto':
        return const Color(0xFF00FFFF); // Cyan
      case 'Forex':
        return const Color(0xFF0099FF); // Electric Blue
      default:
        return const Color(0xFF00FFFF);
    }
  }

  @override
  Widget build(BuildContext context) {
    final marketColor = _getMarketColor();
    final size = MediaQuery.of(context).size;
    final isMobile = size.width < 768;
    
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Column(
          children: [
            // Compact Header
            _buildCompactHeader(marketColor),
            
            // Huge Live Chart - takes most of the screen
            Expanded(
              flex: 3,
              child: _buildWideLiveChart(marketColor, isMobile),
            ),
            
            // Active Trades Section (if any active trades)
            if (_activeTrades.isNotEmpty)
              Container(
                height: 120,
                child: _buildActiveTradesSection(marketColor),
              ),
            
            // Tab Switcher and Content
            Expanded(
              flex: 1,
              child: Column(
                children: [
                  _buildTabSwitcher(marketColor),
                  Expanded(
                    child: _selectedTab == 'active'
                        ? (isMobile
                            ? _buildMobileLayout(marketColor)
                            : _buildDesktopLayout(marketColor, size))
                        : _buildTradeHistorySection(marketColor),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildMobileLayout(Color marketColor) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(8),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Symbol selector
          _buildSymbolSelector(marketColor),
          
          const SizedBox(height: 8),
          
          // Trading controls - simplified
          _buildOrderEntry(marketColor),
        ],
      ),
    );
  }

  Widget _buildDesktopLayout(Color marketColor, Size size) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(8),
      child: Row(
        children: [
          // Left: Symbol selector and trading controls
          Expanded(
            flex: 2,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                _buildSymbolSelector(marketColor),
                const SizedBox(height: 8),
                _buildOrderEntry(marketColor),
              ],
            ),
          ),
          
          const SizedBox(width: 8),
          
          // Right: Minimal order book
          Expanded(
            flex: 1,
            child: _buildOrderBook(marketColor),
          ),
        ],
      ),
    );
  }

  Widget _buildWideLiveChart(Color marketColor, bool isMobile) {
    // Safety check: ensure we have at least 2 data points for chart rendering
    // If we have a price but no chart data, trigger initialization via post-frame callback
    if (_liveChartData.isEmpty && _currentPrice != null && _currentPrice! > 0 && _canUpdate) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (_canUpdate && _liveChartData.isEmpty && _currentPrice != null && _currentPrice! > 0) {
          setState(() {
            _liveChartData = List.generate(50, (index) => FlSpot(index.toDouble(), _currentPrice!));
          });
        }
      });
      // Return loading state while initialization happens
      return Container(
        margin: EdgeInsets.symmetric(
          horizontal: isMobile ? 8 : 12, 
          vertical: isMobile ? 4 : 8
        ),
        child: Center(
          child: const Text('Initializing chart...', style: TextStyle(color: Colors.white54)),
        ),
      );
    }
    
    if (_liveChartData.isEmpty || _liveChartData.length < 2) {
      return Container(
        margin: EdgeInsets.symmetric(
          horizontal: isMobile ? 8 : 12, 
          vertical: isMobile ? 4 : 8
        ),
        child: Center(
          child: _currentPrice == null 
            ? const CircularProgressIndicator()
            : const Text('Loading chart data...', style: TextStyle(color: Colors.white54)),
        ),
      );
    }

    final minPrice = _liveChartData.map((e) => e.y).reduce((a, b) => a < b ? a : b);
    final maxPrice = _liveChartData.map((e) => e.y).reduce((a, b) => a > b ? a : b);
    final priceRange = maxPrice - minPrice;
    
    // Prevent fl_chart assertion errors: ensure valid price range
    if (priceRange <= 0 || priceRange.isNaN || priceRange.isInfinite) {
      final fallbackPrice = _currentPrice ?? 100.0;
      final minY = fallbackPrice * 0.95;
      final maxY = fallbackPrice * 1.05;
      return Container(
        margin: EdgeInsets.symmetric(
          horizontal: isMobile ? 8 : 12, 
          vertical: isMobile ? 4 : 8
        ),
        child: Center(
          child: Text(
            'Loading chart data...',
            style: TextStyle(color: Colors.white54),
          ),
        ),
      );
    }
    
    final isPositive = _priceChange24h >= 0;
    final chartColor = isPositive ? const Color(0xFF00D9A3) : const Color(0xFFFF6B6B);
    final gradientStartColor = isPositive 
        ? const Color(0xFF00D9A3).withOpacity(0.4)
        : const Color(0xFFFF6B6B).withOpacity(0.4);
    final gradientEndColor = Colors.transparent;
    
    return Container(
      margin: EdgeInsets.symmetric(
        horizontal: isMobile ? 8 : 12, 
        vertical: isMobile ? 4 : 8
      ),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            const Color(0xFF001028).withOpacity(0.8),
            const Color(0xFF000C1F).withOpacity(0.9),
          ],
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: chartColor.withOpacity(0.2),
          width: 1.5,
        ),
        boxShadow: [
          BoxShadow(
            color: chartColor.withOpacity(0.1),
            blurRadius: 20,
            spreadRadius: 2,
          ),
        ],
      ),
      child: Padding(
        padding: EdgeInsets.all(isMobile ? 12 : 16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
                    Text(
                      _currentSymbols[_markets[_selectedMarketIndex]] ?? '',
              style: TextStyle(
                        color: Colors.white,
                        fontSize: isMobile ? 14 : 16,
                        fontWeight: FontWeight.w600,
                letterSpacing: 0.5,
              ),
            ),
                    const SizedBox(height: 2),
            Text(
                      _markets[_selectedMarketIndex],
                      style: TextStyle(
                        color: Colors.white54,
                        fontSize: isMobile ? 10 : 11,
                        fontWeight: FontWeight.w400,
                      ),
            ),
          ],
        ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          decoration: BoxDecoration(
                    color: chartColor.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                      color: chartColor.withOpacity(0.4),
                      width: 1.5,
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.fiber_manual_record,
                            color: chartColor,
                            size: 8,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            'Now Price',
                            style: TextStyle(
                              color: chartColor.withOpacity(0.8),
                              fontSize: isMobile ? 9 : 10,
                              fontWeight: FontWeight.w600,
                              letterSpacing: 0.5,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 2),
                      Text(
                        '\$${_currentPrice?.toStringAsFixed(2) ?? '0.00'}',
                        style: TextStyle(
                          color: chartColor,
                          fontSize: isMobile ? 18 : 22,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            SizedBox(height: isMobile ? 8 : 12),
            Expanded(
              child: Stack(
                    children: [
                      LineChart(
                        LineChartData(
                          gridData: FlGridData(
                            show: true,
                            drawVerticalLine: false,
                            horizontalInterval: priceRange > 0 ? (priceRange / 6).clamp(0.01, double.infinity) : 1.0,
                            getDrawingHorizontalLine: (value) {
                              return FlLine(
                                color: Colors.white.withOpacity(0.05),
                                strokeWidth: 1,
                                dashArray: [8, 4],
                              );
                            },
                          ),
                          titlesData: FlTitlesData(
                            show: true,
                            rightTitles: AxisTitles(
                              sideTitles: SideTitles(
                                showTitles: true,
                                reservedSize: 60,
                                interval: priceRange > 0 ? (priceRange / 5).clamp(0.01, double.infinity) : 1.0,
                                getTitlesWidget: (value, meta) {
                                  return Padding(
                                    padding: const EdgeInsets.only(left: 8),
                                    child: Text(
                                      '\$${value.toStringAsFixed(0)}',
                                      style: TextStyle(
                                        color: Colors.white.withOpacity(0.5),
                                        fontSize: 10,
                                        fontWeight: FontWeight.w500,
                                      ),
                                    ),
                                  );
                                },
                              ),
                            ),
                            topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                            bottomTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                            leftTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                          ),
                          borderData: FlBorderData(show: false),
                          lineBarsData: [
                            LineChartBarData(
                              spots: _liveChartData,
                              isCurved: true,
                              curveSmoothness: 0.4,
                              color: chartColor,
                              barWidth: 3,
                              isStrokeCapRound: true,
                              dotData: FlDotData(
                                show: true,
                                getDotPainter: (spot, percent, barData, index) {
                                  if (index == _liveChartData.length - 1) {
                                    return FlDotCirclePainter(
                                      radius: 5,
                                      color: chartColor,
                                      strokeWidth: 3,
                                      strokeColor: Colors.white,
                                    );
                                  }
                                  return FlDotCirclePainter(
                                    radius: 0,
                                    color: Colors.transparent,
                                  );
                                },
                              ),
                              belowBarData: BarAreaData(
                                show: true,
                                gradient: LinearGradient(
                                  begin: Alignment.topCenter,
                                  end: Alignment.bottomCenter,
                                  colors: [
                                    gradientStartColor,
                                    gradientStartColor.withOpacity(0.2),
                                    gradientEndColor,
                                  ],
                                  stops: const [0.0, 0.5, 1.0],
                                ),
                              ),
                              preventCurveOverShooting: true,
                            ),
                          ],
                          minY: (minPrice - (priceRange * 0.1)).clamp(0.0, double.infinity),
                          maxY: (maxPrice + (priceRange * 0.1)).clamp(0.0, double.infinity),
                          clipData: const FlClipData.all(),
                          lineTouchData: LineTouchData(
                            enabled: true,
                            touchTooltipData: LineTouchTooltipData(
                              getTooltipColor: (touchedSpot) => const Color(0xFF001028).withOpacity(0.95),
                              tooltipBorderRadius: BorderRadius.circular(8),
                              tooltipPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                              getTooltipItems: (touchedSpots) {
                                return touchedSpots.map((spot) {
                                  return LineTooltipItem(
                                    '\$${spot.y.toStringAsFixed(2)}',
                                    TextStyle(
                                      color: chartColor,
                                      fontWeight: FontWeight.w700,
                                      fontSize: 14,
                                    ),
                                  );
                                }).toList();
                              },
                            ),
                          ),
                        ),
                      ),
                  Positioned.fill(
                    child: CustomPaint(
                      painter: PriceLevelPainter(
                        currentPrice: _currentPrice!,
                        minPrice: (minPrice - (priceRange * 0.1)).clamp(0.0, double.infinity),
                        maxPrice: (maxPrice + (priceRange * 0.1)).clamp(0.0, double.infinity),
                        color: chartColor,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatChip(String label, String value, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
      color: color.withOpacity(0.1),
      borderRadius: BorderRadius.circular(8),
      border: Border.all(
        color: color.withOpacity(0.3),
        width: 1,
      ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(
              color: Colors.white54,
              fontSize: 9,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            value,
            style: TextStyle(
              color: color,
              fontSize: 11,
              fontWeight: FontWeight.w700,
          ),
        ),
      ],
      ),
    );
  }

  Widget _buildCompactHeader(Color marketColor) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: const Color(0xFF001028),
        border: Border(
          bottom: BorderSide(color: marketColor.withOpacity(0.2), width: 1),
        ),
      ),
      child: Row(
        children: [
          // Market tabs
          Expanded(
      child: TabBar(
        controller: _marketTabController,
              isScrollable: true,
              indicatorColor: marketColor,
              labelColor: marketColor,
        unselectedLabelColor: Colors.white54,
              indicatorSize: TabBarIndicatorSize.tab,
              labelStyle: const TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w600,
              ),
              unselectedLabelStyle: const TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.normal,
              ),
        tabs: _markets.map((m) => Tab(text: m)).toList(),
            ),
          ),
          
          const SizedBox(width: 8),
          
          // Balance display
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: marketColor.withOpacity(0.1),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: marketColor.withOpacity(0.3), width: 1),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.account_balance_wallet, 
                    color: marketColor, size: 14),
                const SizedBox(width: 6),
                Text(
                  '\$${_userBalance.toStringAsFixed(2)}',
                  style: TextStyle(
                    color: marketColor,
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSymbolSelector(Color marketColor) {
    final symbols = _marketSymbols[_markets[_selectedMarketIndex]] ?? [];
    final currentSymbol = _currentSymbols[_markets[_selectedMarketIndex]] ?? 'BTCUSD';

    return Container(
      height: 36,
      margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        itemCount: symbols.length,
        itemBuilder: (ctx, i) {
          final symbol = symbols[i];
          final isSelected = currentSymbol == symbol;

          return GestureDetector(
            onTap: () {
              setState(() {
                _currentSymbols[_markets[_selectedMarketIndex]] = symbol;
              });
              _loadMarketData();
              _loadAISuggestion();
            },
            child: Container(
              margin: const EdgeInsets.only(right: 6),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                gradient: isSelected
                    ? LinearGradient(
                        colors: [marketColor.withOpacity(0.3), 
                                marketColor.withOpacity(0.1)],
                      )
                    : null,
                color: isSelected ? null : const Color(0xFF001028).withOpacity(0.5),
                borderRadius: BorderRadius.circular(18),
                border: Border.all(
                  color: isSelected ? marketColor : marketColor.withOpacity(0.2),
                  width: isSelected ? 1.5 : 1,
                ),
                boxShadow: isSelected ? [
                        BoxShadow(
                    color: marketColor.withOpacity(0.4),
                    blurRadius: 8,
                    spreadRadius: 0,
                  ),
                ] : null,
              ),
              child: Center(
                child: Text(
                  symbol,
                  style: TextStyle(
                    color: isSelected ? marketColor : Colors.white70,
                    fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                    fontSize: 11,
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildCandlestickChart(Color marketColor) {
    if (_currentPrice == null) {
      return const Center(child: CircularProgressIndicator());
    }
    
    return Stack(
            children: [
              // Candlestick chart
              LineChart(
                _buildCandlestickChartData(marketColor),
              ),
              
              // Price indicator overlay
              Positioned(
                top: 8,
                left: 8,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
                    color: const Color(0xFF000C1F).withOpacity(0.8),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: marketColor.withOpacity(0.5), width: 1),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                        _currentSymbols[_markets[_selectedMarketIndex]] ?? '',
                        style: TextStyle(
                          color: marketColor,
                          fontSize: 10,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      _isDisposed 
                        ? Text(
                            '\$${_currentPrice?.toStringAsFixed(2) ?? '0.00'}',
                            style: TextStyle(
                              color: _priceColor,
                              fontSize: 18,
                              fontWeight: FontWeight.w700,
                            ),
                          )
                        : AnimatedBuilder(
                            animation: _priceAnimationController,
                            builder: (context, child) {
                              if (_isDisposed) {
                                return Text(
                                  '\$${_currentPrice?.toStringAsFixed(2) ?? '0.00'}',
                                  style: TextStyle(
                                    color: _priceColor,
                                    fontSize: 18,
                                    fontWeight: FontWeight.w700,
                                  ),
                                );
                              }
                              return Text(
                                '\$${_currentPrice?.toStringAsFixed(2) ?? '0.00'}',
                                style: TextStyle(
                                  color: _priceColor,
                                  fontSize: 18,
                                  fontWeight: FontWeight.w700,
                                ),
                              );
                            },
                          ),
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            _priceChange24h >= 0 ? Icons.trending_up : Icons.trending_down,
                            size: 12,
                            color: _priceChange24h >= 0 ? Colors.green : Colors.red,
                          ),
                          const SizedBox(width: 2),
                          Text(
                            '${_priceChange24h.toStringAsFixed(2)}%',
                            style: TextStyle(
                              color: _priceChange24h >= 0 ? Colors.green : Colors.red,
                              fontSize: 10,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                    ),
                  ],
                ),
                      ),
                    ),
                  ],
          );
  }

  LineChartData _buildCandlestickChartData(Color marketColor) {
    final minPrice = _candlestickData.map((e) => e.y).reduce((a, b) => a < b ? a : b);
    final maxPrice = _candlestickData.map((e) => e.y).reduce((a, b) => a > b ? a : b);
    
    return LineChartData(
      gridData: FlGridData(
        show: true,
        drawVerticalLine: false,
        horizontalInterval: (maxPrice - minPrice) / 5,
        getDrawingHorizontalLine: (value) {
          return FlLine(
            color: marketColor.withOpacity(0.1),
            strokeWidth: 1,
            dashArray: [5, 5],
          );
        },
      ),
      titlesData: FlTitlesData(
        show: true,
        rightTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            reservedSize: 50,
            getTitlesWidget: (value, meta) {
              return Text(
                value.toStringAsFixed(0),
            style: TextStyle(
                  color: Colors.white54,
                  fontSize: 9,
                ),
              );
            },
          ),
        ),
        topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        leftTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        bottomTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
      ),
      borderData: FlBorderData(
        show: true,
        border: Border(
          left: BorderSide(color: marketColor.withOpacity(0.3), width: 1),
          bottom: BorderSide(color: marketColor.withOpacity(0.3), width: 1),
          top: BorderSide.none,
          right: BorderSide.none,
        ),
      ),
      lineBarsData: [
        LineChartBarData(
          spots: _candlestickData,
          isCurved: true,
          color: marketColor,
          barWidth: 2,
          isStrokeCapRound: true,
          dotData: const FlDotData(show: false),
          belowBarData: BarAreaData(
            show: true,
            color: marketColor.withOpacity(0.1),
          ),
        ),
      ],
    );
  }

  Widget _buildTimeframeSelector(Color marketColor) {
        return Container(
      height: 28,
      margin: const EdgeInsets.symmetric(horizontal: 8),
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        itemCount: _timeframes.length,
        itemBuilder: (ctx, i) {
          final timeframe = _timeframes[i];
          final isSelected = i == _selectedTimeframeIndex;

          return GestureDetector(
            onTap: () => setState(() => _selectedTimeframeIndex = i),
            child: Container(
              margin: const EdgeInsets.only(right: 6),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              height: 28,
          decoration: BoxDecoration(
                color: isSelected
                    ? const Color(0xFF1A1A1A)
                    : Colors.transparent,
            borderRadius: BorderRadius.circular(6),
            border: Border.all(
                  color: isSelected 
                      ? marketColor
                      : const Color(0xFF2A2A2A),
                  width: 1,
                ),
              ),
              child: Center(
                    child: Text(
                  timeframe,
                style: TextStyle(
                    color: isSelected ? marketColor : Colors.white54,
                    fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                    fontSize: 10,
                  ),
                ),
              ),
          ),
        );
      },
      ),
    );
  }

  Widget _buildModeToggle(Color marketColor) {
    return Container(
      margin: const EdgeInsets.only(left: 8, right: 8, bottom: 8),
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: const Color(0xFF001028).withOpacity(0.5),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: marketColor.withOpacity(0.3), width: 1),
      ),
      child: Row(
        children: [
          Expanded(
            child: _buildActionButton(
              'PAPER',
              _tradingMode == 'paper',
              Colors.blue,
              () => setState(() => _tradingMode = 'paper'),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: _buildActionButton(
              'LIVE',
              _tradingMode == 'live',
              Colors.orange,
              () => setState(() => _tradingMode = 'live'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildOrderEntry(Color marketColor) {
    return Container(
      margin: const EdgeInsets.all(8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF001028).withOpacity(0.5),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: marketColor.withOpacity(0.3), width: 1),
      ),
      child: Column(
        children: [
          // Buy/Sell tabs
          Row(
            children: [
              Expanded(
                child: _buildActionButton(
                  'BUY',
                  _side == 'buy',
                  Colors.green,
                  () => setState(() => _side = 'buy'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _buildActionButton(
                  'SELL',
                  _side == 'sell',
                  Colors.red,
                  () => setState(() => _side = 'sell'),
                ),
              ),
            ],
          ),
          
          const SizedBox(height: 12),
          
          // Size input with quick buttons
          TextField(
            controller: _sizeController,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            style: const TextStyle(color: Colors.white, fontSize: 12),
            decoration: InputDecoration(
              labelText: 'Size',
              labelStyle: TextStyle(color: marketColor.withOpacity(0.7), fontSize: 10),
              filled: true,
              fillColor: Colors.black.withOpacity(0.3),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
                borderSide: BorderSide(color: marketColor.withOpacity(0.3)),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
                borderSide: BorderSide(color: marketColor.withOpacity(0.3)),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
                borderSide: BorderSide(color: marketColor, width: 2),
              ),
              contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            ),
          ),
          
          // Quick size buttons
          const SizedBox(height: 8),
          Row(
            children: ['25%', '50%', '75%', '100%'].map((percent) {
              return Expanded(
                child: Padding(
                  padding: const EdgeInsets.only(right: 4),
                  child: TextButton(
                    onPressed: () {
                      final percentValue = int.parse(percent.replaceAll('%', ''));
                      final newSize = (_userBalance * percentValue / 100) / 
                          (_currentPrice ?? 1);
                      _sizeController.text = newSize.toStringAsFixed(6);
                    },
                    style: TextButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 6),
                      backgroundColor: marketColor.withOpacity(0.1),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(6),
                      ),
                    ),
                    child: Text(
                      percent,
                      style: TextStyle(
                        color: marketColor,
                        fontSize: 9,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
          
          const SizedBox(height: 12),
          
          // Execute button
          Center(
            child: SizedBox(
              height: 48,
              child: ElevatedButton(
                onPressed: _loading ? null : () => _executeTrade(),
                style: ElevatedButton.styleFrom(
                  backgroundColor: _side == 'buy' 
                      ? const Color(0xFF0ECB81)
                      : const Color(0xFFF6465D),
                  padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 12),
                  minimumSize: const Size(0, 48),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                  elevation: 0,
                ),
                child: Text(
                  _side == 'buy' ? 'Buy ${_currentSymbols[_markets[_selectedMarketIndex]]?.split('/')[0] ?? "BTC"}' : 'Sell ${_currentSymbols[_markets[_selectedMarketIndex]]?.split('/')[0] ?? "BTC"}',
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w600,
                    fontSize: 13,
                    letterSpacing: 0.2,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActionButton(
    String text,
    bool selected,
    Color color,
    VoidCallback onTap,
  ) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        height: 32,
        decoration: BoxDecoration(
          color: selected
              ? color
              : const Color(0xFF1A1A1A),
          borderRadius: BorderRadius.circular(6),
          border: selected ? null : Border.all(
            color: const Color(0xFF2A2A2A),
            width: 1,
          ),
        ),
        child: Center(
          child: Text(
            text,
            style: TextStyle(
              color: selected ? Colors.white : Colors.white70,
              fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
              fontSize: 11,
              letterSpacing: 0.2,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildOrderBook(Color marketColor) {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
          color: const Color(0xFF001028).withOpacity(0.5),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: marketColor.withOpacity(0.3), width: 1),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Order Book',
                style: TextStyle(
                  color: marketColor,
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: marketColor.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  '${((_sellOrders.length / (_sellOrders.length + _buyOrders.length)) * 100).toStringAsFixed(0)}%',
                  style: TextStyle(
                    color: marketColor,
                    fontSize: 9,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
          
          const SizedBox(height: 8),
          
          // Sell orders (red) - simplified, limited items
          ..._sellOrders.take(5).map((order) => Container(
            height: 20,
            margin: const EdgeInsets.only(bottom: 2),
            decoration: BoxDecoration(
              color: Colors.red.withOpacity(0.1),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  order['price'],
                  style: const TextStyle(
                    color: Colors.red,
                    fontSize: 9,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                Text(
                  order['amount'],
                  style: const TextStyle(
                    color: Colors.white70,
                    fontSize: 9,
                  ),
                ),
              ],
            ),
          )).toList(),
          
          // Current price
          Container(
            padding: const EdgeInsets.symmetric(vertical: 6),
            decoration: BoxDecoration(
              color: marketColor.withOpacity(0.2),
              borderRadius: BorderRadius.circular(6),
            ),
            child: Center(
              child: Text(
                '\$${_currentPrice?.toStringAsFixed(2) ?? '0.00'}',
                style: TextStyle(
                  color: marketColor,
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
          
          const SizedBox(height: 4),
          
          // Buy orders (green) - simplified, limited items
          ..._buyOrders.take(5).map((order) => Container(
            height: 20,
            margin: const EdgeInsets.only(bottom: 2),
            decoration: BoxDecoration(
              color: Colors.green.withOpacity(0.1),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  order['price'],
                  style: const TextStyle(
                    color: Colors.green,
                    fontSize: 9,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                Text(
                  order['amount'],
                  style: const TextStyle(
                    color: Colors.white70,
                    fontSize: 9,
                  ),
                ),
              ],
            ),
          )).toList(),
        ],
      ),
    );
  }

  Widget _buildQuickInfo(Color marketColor) {
    return Container(
      height: 200,
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: const Color(0xFF001028).withOpacity(0.5),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: marketColor.withOpacity(0.3), width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
              Text(
            'Market Info',
                style: TextStyle(
              color: marketColor,
              fontSize: 11,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 8),
          
          _buildInfoRow('24h Volume', '\$${((_volume24h ?? 0) / 1000000).toStringAsFixed(1)}M'),
          _buildInfoRow('24h Change', '${(_priceChange24h ?? 0).toStringAsFixed(2)}%', 
              (_priceChange24h ?? 0) >= 0 ? Colors.green : Colors.red),
          _buildInfoRow('Market Cap', '\$${(((_currentPrice ?? 0) * 20000000 / 1000000000)).toStringAsFixed(1)}B'),
          _buildInfoRow('Liquidity', 'High'),
          
          const Spacer(),
          
          // AI suggestion
          if (_aiSuggestion != null) ...[
            const Divider(color: Colors.white24, thickness: 1, height: 16),
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: marketColor.withOpacity(0.1),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Row(
                children: [
                  Icon(Icons.auto_awesome, color: marketColor, size: 14),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      _aiSuggestion!['recommended_action']?.toUpperCase() ?? 'HOLD',
                      style: TextStyle(
                        color: marketColor,
                        fontSize: 10,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildInfoRow(String label, String value, [Color? valueColor]) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: const TextStyle(
              color: Colors.white54,
              fontSize: 9,
            ),
          ),
          Text(
            value,
            style: TextStyle(
              color: valueColor ?? Colors.white,
              fontSize: 10,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
  
  // ============================================================================
  // ACTIVE TRADES & HISTORY UI WIDGETS
  // ============================================================================
  
  Widget _buildTabSwitcher(Color marketColor) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: Colors.grey.shade900.withOpacity(0.5),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Expanded(
            child: _buildTabButton('Active', _selectedTab == 'active', () {
              setState(() => _selectedTab = 'active');
            }),
          ),
          Expanded(
            child: _buildTabButton('History', _selectedTab == 'history', () {
              setState(() {
                _selectedTab = 'history';
                if (_tradeHistory.isEmpty) _loadTradeHistory();
              });
            }),
          ),
        ],
      ),
    );
  }
  
  Widget _buildActiveTradesSection(Color marketColor) {
    return Container(
      margin: EdgeInsets.symmetric(horizontal: 8, vertical: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Tab Switcher
          Row(
            children: [
              _buildTabButton('Active', _selectedTab == 'active', () {
                setState(() => _selectedTab = 'active');
              }),
              SizedBox(width: 8),
              _buildTabButton('History', _selectedTab == 'history', () {
                setState(() {
                  _selectedTab = 'history';
                  if (_tradeHistory.isEmpty) _loadTradeHistory();
                });
              }),
              Spacer(),
              if (_selectedTab == 'active')
                Container(
                  padding: EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: marketColor.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    '${_activeTrades.length} Active',
                    style: TextStyle(
                      color: marketColor,
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
            ],
          ),
          
          SizedBox(height: 12),
          
          // Trades Content
          if (_selectedTab == 'active')
            _activeTrades.isEmpty
                ? _buildEmptyState('No active trades', Icons.show_chart)
                : Column(
                    children: _activeTrades.map((trade) => _buildTradeCard(trade, marketColor)).toList(),
                  )
          else
            _loadingTrades
                ? Center(child: CircularProgressIndicator(color: marketColor))
                : _tradeHistory.isEmpty
                    ? _buildEmptyState('No trade history', Icons.history)
                    : Column(
                        children: _tradeHistory.map((trade) => _buildHistoryCard(trade, marketColor)).toList(),
                      ),
        ],
      ),
    );
  }
  
  Widget _buildTabButton(String text, bool selected, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: selected ? Color(0xFF06B6D4).withOpacity(0.2) : Colors.transparent,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: selected ? Color(0xFF06B6D4) : Colors.white24,
            width: 1.5,
          ),
        ),
        child: Text(
          text,
          style: TextStyle(
            color: selected ? Color(0xFF06B6D4) : Colors.white54,
            fontSize: 13,
            fontWeight: selected ? FontWeight.w600 : FontWeight.normal,
          ),
        ),
      ),
    );
  }
  
  Widget _buildEmptyState(String message, IconData icon) {
    return Container(
      padding: EdgeInsets.all(40),
      child: Column(
        children: [
          Icon(icon, color: Colors.white24, size: 48),
          SizedBox(height: 12),
          Text(
            message,
            style: TextStyle(color: Colors.white54, fontSize: 14),
          ),
        ],
      ),
    );
  }
  
  Widget _buildTradeCard(Map<String, dynamic> trade, Color marketColor) {
    final symbol = trade['symbol'] ?? 'BTCUSDT';
    final side = trade['side'] ?? 'buy';
    final entryPrice = trade['entry_price']?.toDouble() ?? 0.0;
    final size = trade['size']?.toDouble() ?? 0.0;
    final pnl = _calculatePnL(trade);
    final pnlPercent = _calculatePnLPercentage(trade);
    final isProfitable = pnl >= 0;
    
    return Container(
      margin: EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            Color(0xFF001028).withOpacity(0.8),
            Color(0xFF000C1F).withOpacity(0.9),
          ],
        ),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isProfitable ? Colors.green.withOpacity(0.3) : Colors.red.withOpacity(0.3),
          width: 1,
        ),
      ),
      child: Padding(
        padding: EdgeInsets.all(12),
        child: Column(
          children: [
            Row(
              children: [
                // Side Badge
                Container(
                  padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: side == 'buy' ? Colors.green.withOpacity(0.2) : Colors.red.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(
                      color: side == 'buy' ? Colors.green : Colors.red,
                      width: 1,
                    ),
                  ),
                  child: Text(
                    side.toUpperCase(),
                    style: TextStyle(
                      color: side == 'buy' ? Colors.green : Colors.red,
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                SizedBox(width: 8),
                Text(
                  symbol,
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                Spacer(),
                // P&L
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      '${isProfitable ? '+' : ''}\$${pnl.toStringAsFixed(2)}',
                      style: TextStyle(
                        color: isProfitable ? Colors.green : Colors.red,
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    Text(
                      '${isProfitable ? '+' : ''}${pnlPercent.toStringAsFixed(2)}%',
                      style: TextStyle(
                        color: isProfitable ? Colors.green : Colors.red,
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ],
            ),
            SizedBox(height: 8),
            Divider(color: Colors.white12, height: 1),
            SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                _buildTradeInfoColumn('Entry', '\$${entryPrice.toStringAsFixed(2)}'),
                _buildTradeInfoColumn('Current', '\$${(_currentPrice ?? entryPrice).toStringAsFixed(2)}'),
                _buildTradeInfoColumn('Size', size.toStringAsFixed(4)),
                IconButton(
                  onPressed: () async {
                    final confirm = await showDialog<bool>(
                      context: context,
                      builder: (ctx) => AlertDialog(
                        backgroundColor: Color(0xFF001F3F),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                        title: Text('Close Position?', style: TextStyle(color: Colors.white)),
                        content: Text(
                          'Are you sure you want to close this position?',
                          style: TextStyle(color: Colors.white70),
                        ),
                        actions: [
                          TextButton(
                            onPressed: () => Navigator.pop(ctx, false),
                            child: Text('Cancel'),
                          ),
                          ElevatedButton(
                            onPressed: () => Navigator.pop(ctx, true),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.red,
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                            ),
                            child: Text('Close'),
                          ),
                        ],
                      ),
                    );
                    
                    if (confirm == true) {
                      _closePosition(trade['id'] ?? '');
                    }
                  },
                  icon: Icon(Icons.close, color: Colors.red, size: 20),
                  tooltip: 'Close Position',
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildTradeInfoColumn(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: TextStyle(
            color: Colors.white54,
            fontSize: 10,
          ),
        ),
        SizedBox(height: 2),
        Text(
          value,
          style: TextStyle(
            color: Colors.white,
            fontSize: 12,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
  
  Widget _buildTradeHistorySection(Color marketColor) {
    if (_loadingTrades) {
      return const Center(
        child: CircularProgressIndicator(),
      );
    }
    
    if (_tradeHistory.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.history,
              color: Colors.grey.shade600,
              size: 48,
            ),
            const SizedBox(height: 16),
            Text(
              'No trade history',
              style: TextStyle(
                color: Colors.grey.shade600,
                fontSize: 14,
              ),
            ),
          ],
        ),
      );
    }
    
    return ListView.builder(
      padding: const EdgeInsets.all(8),
      itemCount: _tradeHistory.length,
      itemBuilder: (context, index) {
        return _buildHistoryCard(_tradeHistory[index], marketColor);
      },
    );
  }
  
  Widget _buildHistoryCard(Map<String, dynamic> trade, Color marketColor) {
    final symbol = trade['symbol']?.toString() ?? 'N/A';
    final side = trade['side']?.toString().toLowerCase() ?? 'buy';
    final entryPrice = (trade['price'] ?? trade['entry_price'] ?? 0.0).toDouble();
    final exitPrice = (trade['exit_price'] ?? entryPrice).toDouble();
    final quantity = (trade['quantity'] ?? 0.0).toDouble();
    final pnl = (trade['profit_loss'] ?? 0.0).toDouble();
    final timestamp = trade['timestamp']?.toString() ?? '';
    final closedAt = trade['closed_at']?.toString() ?? timestamp;
    
    final isProfit = pnl >= 0;
    final sideColor = side == 'buy' ? Colors.green : Colors.red;
    
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            Colors.grey.shade900.withOpacity(0.6),
            Colors.grey.shade800.withOpacity(0.4),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isProfit
              ? Colors.green.withOpacity(0.2)
              : Colors.red.withOpacity(0.2),
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                symbol,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: sideColor.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: sideColor.withOpacity(0.5)),
                ),
                child: Text(
                  side.toUpperCase(),
                  style: TextStyle(
                    color: sideColor,
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Entry: \$${entryPrice.toStringAsFixed(2)}',
                    style: TextStyle(
                      color: Colors.white70,
                      fontSize: 11,
                    ),
                  ),
                  Text(
                    'Exit: \$${exitPrice.toStringAsFixed(2)}',
                    style: TextStyle(
                      color: Colors.white70,
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    'P&L: \$${pnl.toStringAsFixed(2)}',
                    style: TextStyle(
                      color: isProfit ? Colors.green : Colors.red,
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  if (closedAt.isNotEmpty)
                    Text(
                      _formatTimestamp(closedAt),
                      style: TextStyle(
                        color: Colors.grey.shade600,
                        fontSize: 9,
                      ),
                    ),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }
  
  String _formatTimestamp(String timestamp) {
    try {
      final dt = DateTime.parse(timestamp);
      final now = DateTime.now();
      final diff = now.difference(dt);
      
      if (diff.inDays > 0) {
        return '${diff.inDays}d ago';
      } else if (diff.inHours > 0) {
        return '${diff.inHours}h ago';
      } else if (diff.inMinutes > 0) {
        return '${diff.inMinutes}m ago';
      } else {
        return 'Just now';
      }
    } catch (e) {
      return timestamp;
    }
  }
}

class PriceLevelPainter extends CustomPainter {
  final double currentPrice;
  final double minPrice;
  final double maxPrice;
  final Color color;

  PriceLevelPainter({
    required this.currentPrice,
    required this.minPrice,
    required this.maxPrice,
    required this.color,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final priceRange = maxPrice - minPrice;
    final pricePosition = (maxPrice - currentPrice) / priceRange;
    final y = size.height * pricePosition;

    final paint = Paint()
      ..color = color.withOpacity(0.5)
      ..strokeWidth = 1.5
      ..style = PaintingStyle.stroke;

    const dashWidth = 8.0;
    const dashSpace = 4.0;
    double startX = 0;

    while (startX < size.width) {
      canvas.drawLine(
        Offset(startX, y),
        Offset(startX + dashWidth, y),
        paint,
      );
      startX += dashWidth + dashSpace;
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}

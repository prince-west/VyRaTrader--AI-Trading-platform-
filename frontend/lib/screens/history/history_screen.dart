// lib/screens/history/history_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../../core/api_client.dart';
import '../../models/trade.dart';
import '../../providers/trades_provider.dart';
import '../../providers/auth_provider.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  final List<Trade> _trades = [];
  bool _loading = true;
  String _filter = 'all'; // 'all', 'open', 'closed'
  final DateFormat _dateFormat = DateFormat('MMM dd, yyyy');

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  Future<void> _loadHistory() async {
    setState(() => _loading = true);
    
    try {
      final tradesProvider = Provider.of<TradesProvider>(context, listen: false);
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      final userId = authProvider.user?.id ?? '';
      
      if (userId.isNotEmpty) {
        // Load history from API
        await tradesProvider.loadHistory(userId: userId);
        final trades = tradesProvider.trades;
        
        setState(() {
          _trades.clear();
          _trades.addAll(trades);
          _loading = false;
        });
      } else {
        setState(() {
          _loading = false;
          _trades.clear(); // Don't show demo trades - show empty state
        });
      }
    } catch (e) {
      debugPrint('Failed to load trade history: $e');
      setState(() {
        _loading = false;
        _trades.clear(); // Don't show demo trades
      });
    }
  }

  List<Trade> get _filteredTrades {
    if (_filter == 'all') return _trades;
    if (_filter == 'open') return _trades.where((t) => t.isOpen).toList();
    if (_filter == 'closed') return _trades.where((t) => t.isClosed).toList();
    return _trades;
  }

  List<Trade> _getDemoTrades() {
    final now = DateTime.now();
    return [
      Trade(
        id: '1',
        userId: 'user1',
        symbol: 'BTCUSD',
        strategy: 'momentum',
        side: 'buy',
        size: 0.5,
        price: 50500.0,
        status: 'closed',
        profitLoss: 1250.0,
        currency: 'GHS',
        openedAt: now.subtract(const Duration(days: 2)),
        closedAt: now.subtract(const Duration(days: 1)),
      ),
      Trade(
        id: '2',
        userId: 'user1',
        symbol: 'ETHUSD',
        strategy: 'mean_reversion',
        side: 'sell',
        size: 5.0,
        price: 2950.0,
        status: 'executed',
        profitLoss: 0.0,
        currency: 'GHS',
        openedAt: now.subtract(const Duration(hours: 5)),
      ),
      Trade(
        id: '3',
        userId: 'user1',
        symbol: 'EURUSD',
        strategy: 'trend_following',
        side: 'buy',
        size: 10000.0,
        price: 1.085,
        status: 'closed',
        profitLoss: -45.0,
        currency: 'GHS',
        openedAt: now.subtract(const Duration(days: 5)),
        closedAt: now.subtract(const Duration(days: 4)),
      ),
    ];
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _filteredTrades;
    
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Column(
          children: [
            // Header
            _buildHeader(),
            
            // Filter chips
            _buildFilters(),
            
            // Stats summary
            if (filtered.isNotEmpty) _buildStats(),
            
            // Trades list
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : filtered.isEmpty
                      ? _buildEmptyState()
                      : _buildTradesList(filtered),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          Text(
            'Trade History',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w600,
              color: const Color(0xFF00FFFF),
            ),
          ),
          const Spacer(),
          IconButton(
            icon: const Icon(Icons.refresh, color: Color(0xFF00FFFF)),
            onPressed: _loadHistory,
          ),
        ],
      ),
    );
  }

  Widget _buildFilters() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        children: [
          _FilterChip(
            label: 'All',
            isSelected: _filter == 'all',
            onTap: () => setState(() => _filter = 'all'),
          ),
          const SizedBox(width: 8),
          _FilterChip(
            label: 'Open',
            isSelected: _filter == 'open',
            onTap: () => setState(() => _filter = 'open'),
          ),
          const SizedBox(width: 8),
          _FilterChip(
            label: 'Closed',
            isSelected: _filter == 'closed',
            onTap: () => setState(() => _filter = 'closed'),
          ),
        ],
      ),
    );
  }

  Widget _buildStats() {
    final closed = _filteredTrades.where((t) => t.isClosed).toList();
    final stats = TradeStats.fromTrades(closed);
    
    // Ensure all values are non-null and valid (check for NaN and Infinity directly since they're already doubles)
    final winRate = (stats.winRate.isNaN || stats.winRate.isInfinite) ? 0.0 : stats.winRate;
    final netProfitLoss = (stats.netProfitLoss.isNaN || stats.netProfitLoss.isInfinite) ? 0.0 : stats.netProfitLoss;
    final totalTrades = stats.totalTrades;
    
    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF001028), Color(0xFF001F3F)],
        ),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF00FFFF).withOpacity(0.3)),
      ),
      child: Row(
        children: [
          Expanded(
            child: _StatItem(
              label: 'Win Rate',
              value: '${winRate.toStringAsFixed(1)}%',
              color: winRate >= 50 ? Colors.green : Colors.red,
            ),
          ),
          Container(width: 1, height: 40, color: const Color(0xFF00FFFF).withOpacity(0.3)),
          Expanded(
            child: _StatItem(
              label: 'Total P&L',
              value: '${netProfitLoss >= 0 ? '+' : ''}${netProfitLoss.toStringAsFixed(2)} GHS',
              color: netProfitLoss >= 0 ? Colors.green : Colors.red,
            ),
          ),
          Container(width: 1, height: 40, color: const Color(0xFF00FFFF).withOpacity(0.3)),
          Expanded(
            child: _StatItem(
              label: 'Trades',
              value: '$totalTrades',
              color: const Color(0xFF00FFFF),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.history, size: 64, color: Colors.grey[600]),
          const SizedBox(height: 16),
            Text(
              'No trades yet',
              style: TextStyle(fontSize: 14, color: Colors.grey[400]),
            ),
          const SizedBox(height: 8),
          Text(
            'Start trading to see your history here',
            style: TextStyle(fontSize: 12, color: Colors.grey[600]),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildTradesList(List<Trade> trades) {
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: trades.length,
      itemBuilder: (context, index) {
        final trade = trades[index];
        return _TradeCard(trade: trade, dateFormat: _dateFormat);
      },
    );
  }
}

// Filter chip widget
class _FilterChip extends StatelessWidget {
  final String label;
  final bool isSelected;
  final VoidCallback onTap;

  const _FilterChip({
    required this.label,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected ? const Color(0xFF00FFFF).withOpacity(0.2) : Colors.transparent,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: isSelected ? const Color(0xFF00FFFF) : Colors.grey[700]!,
            width: isSelected ? 1.5 : 1,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: isSelected ? const Color(0xFF00FFFF) : Colors.grey[400],
            fontSize: 12,
            fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
            letterSpacing: 0.3,
          ),
        ),
      ),
    );
  }
}

// Stat item widget
class _StatItem extends StatelessWidget {
  final String label;
  final String value;
  final Color color;

  const _StatItem({
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          value,
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            color: color,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: TextStyle(
            fontSize: 11,
            color: Colors.grey[400],
          ),
        ),
      ],
    );
  }
}

// Trade card widget
class _TradeCard extends StatelessWidget {
  final Trade trade;
  final DateFormat dateFormat;

  const _TradeCard({
    required this.trade,
    required this.dateFormat,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            const Color(0xFF001028).withOpacity(0.8),
            const Color(0xFF001F3F).withOpacity(0.8),
          ],
        ),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF00FFFF).withOpacity(0.2), width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              // Symbol and side
              Row(
                children: [
                  Text(
                    trade.symbol,
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: Color(0xFF00FFFF),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: trade.isLong 
                          ? Colors.green.withOpacity(0.2)
                          : Colors.red.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      trade.isLong ? 'LONG' : 'SHORT',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: trade.isLong ? Colors.green : Colors.red,
                      ),
                    ),
                  ),
                ],
              ),
              
              // Status
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: trade.isOpen 
                      ? Colors.blue.withOpacity(0.2)
                      : Colors.grey.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  trade.status.toUpperCase(),
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                    color: trade.isOpen ? Colors.blue : Colors.grey,
                  ),
                ),
              ),
            ],
          ),
          
          const SizedBox(height: 12),
          
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Size',
                    style: TextStyle(fontSize: 11, color: Colors.grey[400]),
                  ),
                  Text(
                    '${((trade.size.isNaN || trade.size.isInfinite) ? 0.0 : trade.size).toStringAsFixed(2)}',
                    style: TextStyle(fontSize: 14, color: Colors.grey[200]),
                  ),
                ],
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Price',
                    style: TextStyle(fontSize: 11, color: Colors.grey[400]),
                  ),
                  Text(
                    '\$${((trade.price.isNaN || trade.price.isInfinite) ? 0.0 : trade.price).toStringAsFixed(2)}',
                    style: TextStyle(fontSize: 14, color: Colors.grey[200]),
                  ),
                ],
              ),
              if (trade.isClosed) ...[
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      'P&L',
                      style: TextStyle(fontSize: 11, color: Colors.grey[400]),
                    ),
                    Text(
                      '${((trade.profitLoss.isNaN || trade.profitLoss.isInfinite) ? 0.0 : trade.profitLoss) >= 0 ? '+' : ''}\$${((trade.profitLoss.isNaN || trade.profitLoss.isInfinite) ? 0.0 : trade.profitLoss).toStringAsFixed(2)}',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: ((trade.profitLoss.isNaN || trade.profitLoss.isInfinite) ? 0.0 : trade.profitLoss) >= 0 ? Colors.green : Colors.red,
                      ),
                    ),
                  ],
                ),
              ],
            ],
          ),
          
          const SizedBox(height: 12),
          
          // Date
          Text(
            trade.closedAt != null
                ? 'Closed: ${dateFormat.format(trade.closedAt!)}'
                : 'Opened: ${dateFormat.format(trade.openedAt)}',
            style: TextStyle(fontSize: 11, color: Colors.grey[600]),
          ),
        ],
      ),
    );
  }
}


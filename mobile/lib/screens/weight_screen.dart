import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/theme.dart';
import '../services/api.dart';
import '../state/app_state.dart';
import '../widgets/common.dart';

class WeightScreen extends StatefulWidget {
  const WeightScreen({super.key});
  @override
  State<WeightScreen> createState() => _WeightScreenState();
}

class _WeightScreenState extends State<WeightScreen> {
  Map<String, dynamic>? _trend;
  List<Map<String, dynamic>> _waists = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      _trend = await Api.weightTrend();
    } catch (_) {}
    try {
      _waists = ((await Api.waists()) as List?)?.cast<Map<String, dynamic>>() ?? [];
    } catch (_) {} finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _addWeight() async {
    final c = TextEditingController();
    final kg = await showDialog<double>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('وزنك النهاردة'),
        content: TextField(
          controller: c,
          autofocus: true,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: const InputDecoration(labelText: 'الوزن (كجم)', suffixText: 'كجم'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('إلغاء')),
          ElevatedButton(onPressed: () => Navigator.pop(context, double.tryParse(c.text)), child: const Text('سجّل')),
        ],
      ),
    );
    if (kg == null) return;
    try {
      await Api.addWeight(kg);
      if (mounted) showSnack(context, 'اتسجّل وزنك 👍');
      _load();
    } catch (e) {
      if (mounted) showSnack(context, ApiClient.errorMessage(e), error: true);
    }
  }

  Future<void> _addWaist() async {
    final c = TextEditingController();
    final cm = await showDialog<double>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('محيط الخصر النهاردة'),
        content: TextField(
          controller: c,
          autofocus: true,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: const InputDecoration(labelText: 'محيط الخصر (سم)', suffixText: 'سم'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('إلغاء')),
          ElevatedButton(onPressed: () => Navigator.pop(context, double.tryParse(c.text)), child: const Text('سجّل')),
        ],
      ),
    );
    if (cm == null) return;
    try {
      await Api.addWaist(cm);
      if (!mounted) return;
      showSnack(context, 'اتسجّل محيط خصرك 👍');
      await context.read<AppState>().refreshHome();
      _load();
    } catch (e) {
      if (mounted) showSnack(context, ApiClient.errorMessage(e), error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final points = (_trend?['points'] as List?)?.cast<Map<String, dynamic>>() ?? [];
    final plateau = _trend?['plateau'];
    return Scaffold(
      appBar: AppBar(
        title: const Text('الوزن'),
        actions: [
          IconButton(
            onPressed: _addWaist,
            icon: const Icon(Icons.straighten),
            tooltip: 'سجّل محيط الخصر',
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _addWeight, icon: const Icon(Icons.add), label: const Text('سجّل وزن'), backgroundColor: AppColors.teal),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                SectionCard(
                  child: Column(
                    children: [
                      const Icon(Icons.bolt, color: AppColors.blue),
                      const SizedBox(height: 4),
                      Text(
                        'بنتابع وزنك بالاتجاه (المتوسط) مش الرقم اليومي — لأن الوزن بيتذبذب طبيعي.',
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: AppColors.textMuted, fontSize: 13),
                      ),
                      if (_trend?['suggested_weigh_in_day_ar'] != null) ...[
                        const SizedBox(height: 6),
                        Text('يوم الوزن المفضّل: ${_trend!['suggested_weigh_in_day_ar']} الصبح',
                            style: const TextStyle(fontWeight: FontWeight.w600)),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                if (points.length >= 2)
                  SectionCard(
                    title: 'اتجاه الوزن',
                    child: SizedBox(height: 220, child: _chart(points)),
                  )
                else
                  const SectionCard(child: Text('سجّل وزنك مرتين على الأقل عشان نرسم اتجاهك 🙂', textAlign: TextAlign.center)),
                const SizedBox(height: 12),
                if (plateau != null && plateau['is_plateau'] == true)
                  Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(color: AppColors.orange.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(14)),
                    child: Row(children: [
                      const Icon(Icons.insights, color: AppColors.orange),
                      const SizedBox(width: 10),
                      Expanded(child: Text(plateau['message_ar'] ?? '', style: const TextStyle(color: AppColors.orange))),
                    ]),
                  ),
                const SizedBox(height: 12),
                SectionCard(
                  title: 'محيط الخصر',
                  child: _waists.isEmpty
                      ? const Text('سجّل محيط خصرك من الزرار فوق عشان نتابع نسبة الدهون 🙂',
                          textAlign: TextAlign.center)
                      : Column(
                          children: [
                            for (final w in _waists.take(8))
                              Padding(
                                padding: const EdgeInsets.symmetric(vertical: 4),
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    Text('${(w['waist_cm'] as num?)?.toStringAsFixed(1) ?? '—'} سم',
                                        style: const TextStyle(fontWeight: FontWeight.w600)),
                                    Text('${w['date'] ?? ''}',
                                        style: const TextStyle(color: AppColors.textMuted, fontSize: 13)),
                                  ],
                                ),
                              ),
                          ],
                        ),
                ),
              ],
            ),
    );
  }

  Widget _chart(List<Map<String, dynamic>> points) {
    final raw = <FlSpot>[];
    final trend = <FlSpot>[];
    for (var i = 0; i < points.length; i++) {
      raw.add(FlSpot(i.toDouble(), (points[i]['raw_kg'] as num).toDouble()));
      trend.add(FlSpot(i.toDouble(), (points[i]['trend_kg'] as num).toDouble()));
    }
    return LineChart(LineChartData(
      gridData: const FlGridData(show: true, drawVerticalLine: false),
      titlesData: const FlTitlesData(
        topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
        rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
        bottomTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
      ),
      borderData: FlBorderData(show: false),
      lineBarsData: [
        LineChartBarData(spots: raw, color: AppColors.blue.withValues(alpha: 0.4), barWidth: 2, dotData: const FlDotData(show: false)),
        LineChartBarData(spots: trend, color: AppColors.teal, barWidth: 3.5, dotData: const FlDotData(show: false), isCurved: true),
      ],
    ));
  }
}

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../core/api_client.dart';
import '../core/theme.dart';
import '../services/api.dart';
import '../widgets/common.dart';

class WeightScreen extends StatefulWidget {
  const WeightScreen({super.key});
  @override
  State<WeightScreen> createState() => _WeightScreenState();
}

class _WeightScreenState extends State<WeightScreen> {
  Map<String, dynamic>? _trend;
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

  @override
  Widget build(BuildContext context) {
    final points = (_trend?['points'] as List?)?.cast<Map<String, dynamic>>() ?? [];
    final plateau = _trend?['plateau'];
    return Scaffold(
      appBar: AppBar(title: const Text('الوزن')),
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

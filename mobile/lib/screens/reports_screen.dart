import 'dart:io';

import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import '../core/api_client.dart';
import '../core/theme.dart';
import '../services/api.dart';
import '../widgets/common.dart';

class ReportsScreen extends StatefulWidget {
  const ReportsScreen({super.key});
  @override
  State<ReportsScreen> createState() => _ReportsScreenState();
}

class _ReportsScreenState extends State<ReportsScreen> with SingleTickerProviderStateMixin {
  late final _tabs = TabController(length: 2, vsync: this);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('التقارير'),
        bottom: TabBar(controller: _tabs, tabs: const [Tab(text: 'أسبوعي'), Tab(text: 'شهري')]),
      ),
      body: TabBarView(controller: _tabs, children: const [_WeeklyView(), _MonthlyView()]),
    );
  }
}

const _statusColors = {'ضمن الهدف': AppColors.teal, 'فوق الهدف': AppColors.orange, 'تحت الهدف': AppColors.blue};

Future<void> _sharePdf(BuildContext context, List<int> bytes, String name) async {
  try {
    final dir = await getTemporaryDirectory();
    final file = File('${dir.path}/$name');
    await file.writeAsBytes(bytes);
    await Share.shareXFiles([XFile(file.path)], text: 'تقرير رشاقة');
  } catch (e) {
    if (context.mounted) showSnack(context, 'تعذّرت المشاركة', error: true);
  }
}

class _WeeklyView extends StatefulWidget {
  const _WeeklyView();
  @override
  State<_WeeklyView> createState() => _WeeklyViewState();
}

class _WeeklyViewState extends State<_WeeklyView> {
  Map<String, dynamic>? _r;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      _r = await Api.weeklyReport();
    } catch (_) {} finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    final r = _r;
    if (r == null) return const Center(child: Text('تعذّر تحميل التقرير'));
    final days = (r['days'] as List).cast<Map<String, dynamic>>();
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        SectionCard(
          title: 'أسبوع ${r['start']} → ${r['end']}',
          child: Column(children: [
            _stat('أيام الالتزام', '${r['adherent_days']} من 7'),
            _stat('توزيع الأيام', 'ضمن ${r['days_within']} • فوق ${r['days_over']} • تحت ${r['days_under']}'),
            _stat('متوسط المتناول', '${r['avg_eaten']} سعرة (هدف ${r['avg_target']})'),
            _stat('متوسط الماكروز', 'بروتين ${r['avg_protein']} • نشويات ${r['avg_carbs']} • دهون ${r['avg_fat']}'),
            if ((r['water_avg_ml'] ?? 0) > 0) _stat('متوسط المياه', '${r['water_avg_ml']} مل/يوم'),
            if ((r['activity_total_min'] ?? 0) > 0) _stat('النشاط', '${r['activity_total_min']} دقيقة • ${r['activity_total_calories']} سعرة'),
            if (r['weight_change_kg'] != null) _stat('تغيّر الوزن', '${r['weight_change_kg']} كجم'),
          ]),
        ),
        const SizedBox(height: 12),
        SectionCard(
          title: 'تفصيل الأيام',
          child: Column(
            children: days.map((d) => ListTile(
              contentPadding: EdgeInsets.zero,
              dense: true,
              title: Text('${d['day']}'),
              trailing: Text('${d['eaten_calories'].round()}/${d['target_calories'].round()}'),
              subtitle: Text(
                d['status'] == 'لا يوجد تسجيل'
                    ? d['status']
                    : '${d['status']} • بروتين ${d['protein']} نشويات ${d['carbs']} دهون ${d['fat']}',
                style: TextStyle(color: _statusColors[d['status']] ?? AppColors.textMuted),
              ),
            )).toList(),
          ),
        ),
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(color: AppColors.teal.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(12)),
          child: Text(r['summary_ar'] ?? '', textAlign: TextAlign.center, style: const TextStyle(color: AppColors.tealDark)),
        ),
        const SizedBox(height: 12),
        ElevatedButton.icon(
          icon: const Icon(Icons.share),
          label: const Text('شارك PDF (للطبيب)'),
          onPressed: () async {
            final bytes = await Api.weeklyPdf();
            if (context.mounted) await _sharePdf(context, bytes, 'تقرير_اسبوعي.pdf');
          },
        ),
      ],
    );
  }

  Widget _stat(String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Text(k, style: const TextStyle(color: AppColors.textMuted)),
          Text(v, style: const TextStyle(fontWeight: FontWeight.bold)),
        ]),
      );
}

class _MonthlyView extends StatefulWidget {
  const _MonthlyView();
  @override
  State<_MonthlyView> createState() => _MonthlyViewState();
}

class _MonthlyViewState extends State<_MonthlyView> {
  Map<String, dynamic>? _r;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final now = DateTime.now();
    try {
      _r = await Api.monthlyReport(now.year, now.month);
    } catch (_) {} finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    final r = _r;
    if (r == null) return const Center(child: Text('تعذّر تحميل التقرير'));
    final weeks = (r['weeks'] as List).cast<Map<String, dynamic>>();
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        SectionCard(
          title: 'ملخص الشهر',
          child: Column(children: [
            _stat('إجمالي أيام الالتزام', '${r['total_adherent_days']} يوم'),
            _stat('أيام التسجيل', '${r['total_logged_days']} يوم'),
            _stat('متوسط المتناول', '${r['avg_eaten']} سعرة'),
            _stat('متوسط الماكروز', 'بروتين ${r['avg_protein']} • نشويات ${r['avg_carbs']} • دهون ${r['avg_fat']}'),
            if ((r['water_avg_ml'] ?? 0) > 0) _stat('متوسط المياه', '${r['water_avg_ml']} مل/يوم'),
            if ((r['activity_total_min'] ?? 0) > 0) _stat('النشاط', '${r['activity_total_min']} دقيقة • ${r['activity_total_calories']} سعرة'),
            if (r['weight_change_kg'] != null) _stat('تغيّر الوزن', '${r['weight_change_kg']} كجم'),
          ]),
        ),
        const SizedBox(height: 12),
        SectionCard(
          title: 'مقارنة الأسابيع',
          child: Column(
            children: weeks.asMap().entries.map((e) => ListTile(
              contentPadding: EdgeInsets.zero,
              dense: true,
              leading: CircleAvatar(radius: 14, backgroundColor: AppColors.teal.withValues(alpha: 0.15), child: Text('${e.key + 1}')),
              title: Text('التزام ${e.value['adherent_days']} من 7'),
              trailing: Text('${e.value['avg_eaten']} سعرة'),
            )).toList(),
          ),
        ),
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(color: AppColors.teal.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(12)),
          child: Text(r['summary_ar'] ?? '', textAlign: TextAlign.center, style: const TextStyle(color: AppColors.tealDark)),
        ),
        const SizedBox(height: 12),
        ElevatedButton.icon(
          icon: const Icon(Icons.share),
          label: const Text('شارك PDF (للطبيب)'),
          onPressed: () async {
            final now = DateTime.now();
            final bytes = await Api.monthlyPdf(now.year, now.month);
            if (context.mounted) await _sharePdf(context, bytes, 'تقرير_شهري.pdf');
          },
        ),
      ],
    );
  }

  Widget _stat(String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Text(k, style: const TextStyle(color: AppColors.textMuted)),
          Text(v, style: const TextStyle(fontWeight: FontWeight.bold)),
        ]),
      );
}

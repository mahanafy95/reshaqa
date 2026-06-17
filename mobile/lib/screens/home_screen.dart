import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/theme.dart';
import '../services/api.dart';
import '../services/update_service.dart';
import '../state/app_state.dart';
import '../widgets/common.dart';
import 'activity_screen.dart';
import 'log_food_screen.dart';
import 'mood_screen.dart';
import 'reports_screen.dart';
import 'settings_screen.dart';
import 'water_screen.dart';
import 'weight_screen.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    final s = app.summary;

    return Scaffold(
      appBar: AppBar(
        title: const Text('رشاقة'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings_outlined),
            onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SettingsScreen())),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: AppColors.teal,
        icon: const Icon(Icons.add),
        label: const Text('سجّل أكل'),
        onPressed: () => _openLog(context),
      ),
      body: RefreshIndicator(
        onRefresh: () => app.refreshHome(),
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 90),
          children: [
            const _UpdateBanner(),
            if (s == null)
              const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator()))
            else ...[
              _SummaryCard(summary: s),
              const SizedBox(height: 12),
              _MacrosCard(summary: s),
              const SizedBox(height: 12),
              if (app.water != null) _WaterMini(water: app.water!),
              const SizedBox(height: 12),
              const _BodyMetricsCard(),
              _PlateauBanner(),
              const Text('إجراءات سريعة', style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold)),
              const SizedBox(height: 10),
              GridView.count(
                crossAxisCount: 3,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                mainAxisSpacing: 12,
                crossAxisSpacing: 12,
                childAspectRatio: 0.95,
                children: [
                  QuickAction(icon: Icons.restaurant, label: 'الأكل', onTap: () => _openLog(context)),
                  QuickAction(icon: Icons.monitor_weight_outlined, label: 'الوزن', color: AppColors.blue, onTap: () => _push(context, const WeightScreen())),
                  QuickAction(icon: Icons.water_drop_outlined, label: 'المياه', color: AppColors.blue, onTap: () => _push(context, const WaterScreen())),
                  QuickAction(icon: Icons.directions_run, label: 'النشاط', color: AppColors.orange, onTap: () => _push(context, const ActivityScreen())),
                  QuickAction(icon: Icons.mood, label: 'حاسس بإيه', color: AppColors.orange, onTap: () => _push(context, const MoodScreen())),
                  QuickAction(icon: Icons.bar_chart, label: 'التقارير', onTap: () => _push(context, const ReportsScreen())),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  void _openLog(BuildContext context) async {
    await Navigator.push(context, MaterialPageRoute(builder: (_) => const LogFoodScreen()));
    if (context.mounted) context.read<AppState>().refreshHome();
  }

  void _push(BuildContext context, Widget screen) async {
    await Navigator.push(context, MaterialPageRoute(builder: (_) => screen));
    if (context.mounted) context.read<AppState>().refreshHome();
  }
}

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({required this.summary});
  final Map<String, dynamic> summary;

  @override
  Widget build(BuildContext context) {
    final target = (summary['target_calories'] as num).toDouble();
    final eaten = (summary['eaten_calories'] as num).toDouble();
    final remaining = (summary['remaining_calories'] as num).toDouble();
    final pct = ((summary['percent_of_target'] as num?)?.toDouble() ?? 0) / 100;
    final mode = summary['mode'] == 'maintain' ? 'تثبيت' : 'تخسيس';

    return SectionCard(
      child: Column(
        children: [
          Row(
            children: [
              SizedBox(
                width: 92,
                height: 92,
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    SizedBox(
                      width: 92, height: 92,
                      child: CircularProgressIndicator(
                        value: pct > 1 ? 1 : pct,
                        strokeWidth: 9,
                        backgroundColor: AppColors.teal.withValues(alpha: 0.12),
                        valueColor: AlwaysStoppedAnimation(remaining < 0 ? AppColors.orange : AppColors.teal),
                      ),
                    ),
                    Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text('${eaten.round()}', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                        Text('من ${target.round()}', style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      remaining >= 0 ? 'باقي ${remaining.round()} سعرة' : 'زيادة ${(-remaining).round()} سعرة',
                      style: TextStyle(fontSize: 19, fontWeight: FontWeight.bold, color: remaining < 0 ? AppColors.orange : AppColors.teal),
                    ),
                    const SizedBox(height: 4),
                    Chip(
                      label: Text('وضع $mode'),
                      backgroundColor: AppColors.teal.withValues(alpha: 0.1),
                      visualDensity: VisualDensity.compact,
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(color: AppColors.teal.withValues(alpha: 0.07), borderRadius: BorderRadius.circular(12)),
            child: Text(summary['encouragement_ar'] ?? '', textAlign: TextAlign.center, style: const TextStyle(color: AppColors.tealDark)),
          ),
        ],
      ),
    );
  }
}

class _MacrosCard extends StatelessWidget {
  const _MacrosCard({required this.summary});
  final Map<String, dynamic> summary;

  @override
  Widget build(BuildContext context) {
    final cal = summary['calories_status'] as Map<String, dynamic>;
    final macros = (summary['macros'] as List).cast<Map<String, dynamic>>();
    final colors = {'بروتين': AppColors.teal, 'نشويات': AppColors.orange, 'دهون': AppColors.blue};
    return SectionCard(
      title: 'الماكروز النهاردة',
      child: Column(
        children: [
          for (final m in macros)
            MacroBar(
              name: m['name_ar'],
              eaten: (m['eaten'] as num).toDouble(),
              target: (m['target'] as num).toDouble(),
              color: colors[m['name_ar']] ?? AppColors.teal,
            ),
          const SizedBox(height: 8),
          Text(cal['message_ar'] ?? '', style: const TextStyle(color: AppColors.textMuted), textAlign: TextAlign.center),
        ],
      ),
    );
  }
}

class _WaterMini extends StatelessWidget {
  const _WaterMini({required this.water});
  final Map<String, dynamic> water;

  @override
  Widget build(BuildContext context) {
    final total = water['total_ml'] ?? 0;
    final goal = water['goal_ml'] ?? 1;
    final pct = (total / goal).clamp(0.0, 1.0);
    return SectionCard(
      child: Row(
        children: [
          const Icon(Icons.water_drop, color: AppColors.blue),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('المياه: $total / $goal مل', style: const TextStyle(fontWeight: FontWeight.w600)),
                const SizedBox(height: 4),
                ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: LinearProgressIndicator(value: pct.toDouble(), minHeight: 8, color: AppColors.blue, backgroundColor: AppColors.blue.withValues(alpha: 0.15)),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _UpdateBanner extends StatefulWidget {
  const _UpdateBanner();
  @override
  State<_UpdateBanner> createState() => _UpdateBannerState();
}

class _UpdateBannerState extends State<_UpdateBanner> {
  UpdateInfo? _info;

  @override
  void initState() {
    super.initState();
    UpdateService.check().then((v) {
      if (mounted && v != null) setState(() => _info = v);
    });
  }

  @override
  Widget build(BuildContext context) {
    final info = _info;
    if (info == null) return const SizedBox.shrink();
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        gradient: const LinearGradient(colors: [AppColors.teal, AppColors.tealDark]),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        children: [
          const Icon(Icons.system_update, color: Colors.white),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('تحديث جديد متاح (${info.versionName})',
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                if (info.notes.isNotEmpty)
                  Text(info.notes, style: const TextStyle(color: Colors.white70, fontSize: 12)),
              ],
            ),
          ),
          TextButton(
            onPressed: () => UpdateService.openDownload(info.downloadUrl),
            style: TextButton.styleFrom(backgroundColor: Colors.white),
            child: const Text('حدّث الآن'),
          ),
        ],
      ),
    );
  }
}

class _BodyMetricsCard extends StatefulWidget {
  const _BodyMetricsCard();
  @override
  State<_BodyMetricsCard> createState() => _BodyMetricsCardState();
}

class _BodyMetricsCardState extends State<_BodyMetricsCard> {
  Map<String, dynamic>? _m;

  @override
  void initState() {
    super.initState();
    Api.bodyMetrics().then((v) {
      if (mounted) setState(() => _m = v);
    }).catchError((_) {});
  }

  Widget _row(String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Text(k, style: const TextStyle(color: AppColors.textMuted)),
          Text(v, style: const TextStyle(fontWeight: FontWeight.w600)),
        ]),
      );

  @override
  Widget build(BuildContext context) {
    final m = _m;
    if (m == null) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: SectionCard(
        title: 'مؤشرات الجسم',
        child: Column(
          children: [
            _row('مؤشر الكتلة (BMI)', '${m['bmi']} — ${m['bmi_category_ar']}'),
            _row('النطاق الصحي لوزنك', '${m['healthy_min_kg']} - ${m['healthy_max_kg']} كجم'),
            if (m['body_fat_pct'] != null) _row('نسبة الدهون (تقديرية)', '${m['body_fat_pct']}%'),
            if (m['lean_mass_kg'] != null)
              _row('الكتلة الصافية / الدهون', '${m['lean_mass_kg']} / ${m['fat_mass_kg']} كجم'),
            const SizedBox(height: 4),
            Text(m['note_ar'] ?? '', style: const TextStyle(color: AppColors.textMuted, fontSize: 11)),
          ],
        ),
      ),
    );
  }
}

class _PlateauBanner extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final targets = context.watch<AppState>().targets;
    final plateau = targets?['plateau'];
    if (plateau == null || plateau['is_plateau'] != true) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: AppColors.orange.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(14)),
        child: Row(
          children: [
            const Icon(Icons.insights, color: AppColors.orange),
            const SizedBox(width: 10),
            Expanded(child: Text(plateau['message_ar'] ?? '', style: const TextStyle(color: AppColors.orange))),
          ],
        ),
      ),
    );
  }
}

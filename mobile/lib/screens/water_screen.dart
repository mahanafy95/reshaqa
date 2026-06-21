import 'package:flutter/material.dart';

import '../core/api_client.dart';
import '../core/theme.dart';
import '../services/api.dart';
import '../services/notifications_service.dart';
import '../widgets/common.dart';

class WaterScreen extends StatefulWidget {
  const WaterScreen({super.key});
  @override
  State<WaterScreen> createState() => _WaterScreenState();
}

class _WaterScreenState extends State<WaterScreen> {
  Map<String, dynamic>? _water;
  bool _loading = true;
  List<dynamic> _drinks = [];
  final _customMl = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await Future.wait([Api.water(), Api.drinkSuggestions()]);
      _water = r[0] as Map<String, dynamic>;
      _drinks = r[1] as List<dynamic>;
    } catch (_) {} finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _add(int ml) async {
    try {
      _water = await Api.addWater(ml);
      setState(() {});
    } catch (e) {
      if (mounted) showSnack(context, ApiClient.errorMessage(e), error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final total = _water?['total_ml'] ?? 0;
    final goal = _water?['goal_ml'] ?? 2500;
    final pct = (total / goal).clamp(0.0, 1.0).toDouble();
    return Scaffold(
      appBar: AppBar(title: const Text('المياه')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                SectionCard(
                  child: Column(
                    children: [
                      SizedBox(
                        height: 130, width: 130,
                        child: Stack(alignment: Alignment.center, children: [
                          SizedBox(height: 130, width: 130, child: CircularProgressIndicator(
                            value: pct, strokeWidth: 12, backgroundColor: AppColors.blue.withValues(alpha: 0.12),
                            valueColor: const AlwaysStoppedAnimation(AppColors.blue))),
                          Column(mainAxisSize: MainAxisSize.min, children: [
                            const Icon(Icons.water_drop, color: AppColors.blue, size: 28),
                            Text('$total', style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
                            Text('من $goal مل', style: TextStyle(color: mutedColor(context), fontSize: 12)),
                          ]),
                        ]),
                      ),
                      const SizedBox(height: 12),
                      Text(_water?['message_ar'] ?? '', textAlign: TextAlign.center, style: const TextStyle(color: AppColors.blue)),
                      const SizedBox(height: 12),
                      Wrap(spacing: 10, alignment: WrapAlignment.center, children: [
                        for (final ml in [150, 250, 500])
                          ElevatedButton(
                            style: ElevatedButton.styleFrom(backgroundColor: AppColors.blue, minimumSize: const Size(90, 48)),
                            onPressed: () => _add(ml), child: Text('+$ml مل')),
                      ]),
                      const SizedBox(height: 12),
                      Row(children: [
                        Expanded(
                          child: TextField(
                            controller: _customMl,
                            keyboardType: TextInputType.number,
                            decoration: const InputDecoration(labelText: 'كمية يدوية (مل)', isDense: true),
                          ),
                        ),
                        const SizedBox(width: 8),
                        ElevatedButton(
                          style: ElevatedButton.styleFrom(backgroundColor: AppColors.blue),
                          onPressed: () {
                            final ml = int.tryParse(_customMl.text);
                            if (ml == null || ml <= 0) {
                              showSnack(context, 'اكتب كمية صحيحة بالملّي 💧', error: true);
                              return;
                            }
                            _add(ml);
                            _customMl.clear();
                          },
                          child: const Text('أضف'),
                        ),
                      ]),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                SectionCard(
                  title: '🔔 تذكير شرب المياه',
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text('هدفك اليومي $goal مل (محسوب من وزنك تلقائياً). خلّينا نفكّرك تشرب على مدار اليوم.',
                          style: TextStyle(color: mutedColor(context))),
                      const SizedBox(height: 10),
                      ElevatedButton(
                        style: ElevatedButton.styleFrom(backgroundColor: AppColors.blue),
                        child: const Text('🔔 فعّل تذكيرات شرب المياه'),
                        onPressed: () async {
                          await NotificationsService.requestPermissions();
                          await NotificationsService.scheduleWaterReminders();
                          if (mounted) {
                            showSnack(context, 'تمام ✅ هتوصلك تنبيهات شرب المياه على مدار اليوم (بصوت حتى لو صامت)');
                          }
                        },
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                SectionCard(
                  title: 'مشروبات تساعدك',
                  child: Column(
                    children: _drinks.map((d) => ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(Icons.local_drink_outlined, color: AppColors.blue),
                      title: Text(d['name_ar']),
                      subtitle: Text(d['note_ar']),
                      trailing: Text('${d['approx_calories']} سعرة', style: TextStyle(color: mutedColor(context))),
                    )).toList(),
                  ),
                ),
              ],
            ),
    );
  }
}

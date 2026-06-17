import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/theme.dart';
import '../services/biometric_service.dart';
import '../services/notifications_service.dart';
import '../state/app_state.dart';
import '../widgets/common.dart';
import 'setup_profile_screen.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});
  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  bool _notifications = false;
  bool _lock = false;
  bool _loading = true;
  static const _kNotif = 'reshaqa_notifications';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    _notifications = prefs.getBool(_kNotif) ?? false;
    _lock = await BiometricService.isLockEnabled();
    setState(() => _loading = false);
  }

  Future<void> _toggleNotifications(bool v) async {
    final prefs = await SharedPreferences.getInstance();
    if (v) {
      await NotificationsService.requestPermissions();
      await NotificationsService.scheduleAll();
      if (mounted) showSnack(context, 'فعّلنا تذكيرات المياه والأكل ووزن الجمعة 🔔');
    } else {
      await NotificationsService.cancelAll();
    }
    await prefs.setBool(_kNotif, v);
    setState(() => _notifications = v);
  }

  Future<void> _toggleLock(bool v) async {
    if (v) {
      final ok = await BiometricService.canCheck();
      if (!ok) {
        if (mounted) showSnack(context, 'جهازك مش مفعّل عليه قفل/بصمة', error: true);
        return;
      }
      final auth = await BiometricService.authenticate();
      if (!auth) return;
    }
    await BiometricService.setLockEnabled(v);
    setState(() => _lock = v);
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    if (_loading) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    return Scaffold(
      appBar: AppBar(title: const Text('الإعدادات')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          SectionCard(
            title: 'التذكيرات',
            child: Column(children: [
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('تذكيرات المياه والأكل ووزن الجمعة'),
                subtitle: const Text('منبّه المياه بيطلع صوت حتى لو الموبايل صامت'),
                value: _notifications,
                onChanged: _toggleNotifications,
              ),
            ]),
          ),
          const SizedBox(height: 12),
          SectionCard(
            title: 'الأمان',
            child: SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('قفل التطبيق ببصمة/رقم سري'),
              value: _lock,
              onChanged: _toggleLock,
            ),
          ),
          const SizedBox(height: 12),
          SectionCard(
            title: 'بياناتي',
            child: Column(children: [
              if (app.profile != null) ...[
                _info('الوزن الحالي', '${app.profile!['weight_kg']} كجم'),
                _info('الطول', '${app.profile!['height_cm']} سم'),
                if (app.profile!['goal_weight_kg'] != null)
                  _info('الوزن المستهدف', '${app.profile!['goal_weight_kg']} كجم'),
                _info('النطاق الصحي', '${app.profile!['healthy_min_kg']} - ${app.profile!['healthy_max_kg']} كجم'),
              ],
              const SizedBox(height: 8),
              OutlinedButton.icon(
                icon: const Icon(Icons.edit),
                label: const Text('تعديل بياناتي'),
                onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SetupProfileScreen())),
              ),
            ]),
          ),
          const SizedBox(height: 12),
          SectionCard(
            title: 'مزامنة الصحة',
            child: const Text(
              'الأولوية لهواوي الصحة ثم Health Connect ثم الإدخال اليدوي. '
              'السعرات المحروقة بتتعرض كنشاط بس وما بتتخصمش من ميزانية الأكل.',
              style: TextStyle(color: AppColors.textMuted),
            ),
          ),
          const SizedBox(height: 20),
          OutlinedButton.icon(
            style: OutlinedButton.styleFrom(foregroundColor: AppColors.danger, minimumSize: const Size.fromHeight(50)),
            icon: const Icon(Icons.logout),
            label: const Text('تسجيل الخروج'),
            onPressed: () => context.read<AppState>().logout(),
          ),
          const SizedBox(height: 20),
          const Center(child: Text('رشاقة • نسخة 1.0', style: TextStyle(color: AppColors.textMuted))),
          const Center(child: Text('أداة توعية وليست بديلاً عن استشارة طبية', style: TextStyle(color: AppColors.textMuted, fontSize: 12))),
        ],
      ),
    );
  }

  Widget _info(String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Text(k, style: const TextStyle(color: AppColors.textMuted)),
          Text(v, style: const TextStyle(fontWeight: FontWeight.bold)),
        ]),
      );
}

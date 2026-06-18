import 'package:flutter/material.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/api_client.dart';
import '../core/theme.dart';
import '../services/api.dart';
import '../services/biometric_service.dart';
import '../services/notifications_service.dart';
import '../state/app_state.dart';
import '../widgets/common.dart';
import 'paywall_screen.dart';
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
  bool _restoring = false;
  String _version = '';
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
    try {
      final info = await PackageInfo.fromPlatform();
      _version = '${info.version} (${info.buildNumber})';
    } catch (_) {
      _version = '—';
    }
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
            title: 'الاشتراك',
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              app.isPremium
                  ? const Row(children: [
                      Text('💎', style: TextStyle(fontSize: 22)),
                      SizedBox(width: 10),
                      Expanded(
                        child: Text('مشترك في Premium — كل المميزات مفتوحة. شكراً لدعمك 💚',
                            style: TextStyle(fontWeight: FontWeight.w600)),
                      ),
                    ])
                  : Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                      const Text('افتح التقارير المفصّلة + PDF، الوصفات بلا حدود + الباركود، '
                          'ومزامنة الصحة مع Premium.',
                          style: TextStyle(color: AppColors.textMuted)),
                      const SizedBox(height: 10),
                      ElevatedButton.icon(
                        icon: const Text('💎', style: TextStyle(fontSize: 16)),
                        label: const Text('اشترك في Premium'),
                        onPressed: () => Navigator.push(context,
                            MaterialPageRoute(builder: (_) => const PaywallScreen())),
                      ),
                    ]),
              const SizedBox(height: 8),
              TextButton.icon(
                icon: const Icon(Icons.restore, size: 20),
                label: const Text('استعادة المشتريات'),
                onPressed: _restoring ? null : () => _restorePurchases(context),
              ),
            ]),
          ),
          const SizedBox(height: 12),
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
              _info('البريد الإلكتروني', app.email ?? 'مش مضاف'),
              const SizedBox(height: 8),
              OutlinedButton.icon(
                icon: const Icon(Icons.alternate_email),
                label: Text(app.email == null ? 'إضافة البريد' : 'تغيير البريد'),
                onPressed: () => _editEmail(context),
              ),
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
            onPressed: () => _confirmLogout(context),
          ),
          const SizedBox(height: 10),
          TextButton.icon(
            style: TextButton.styleFrom(foregroundColor: AppColors.danger),
            icon: const Icon(Icons.delete_forever_outlined, size: 20),
            label: const Text('حذف حسابي نهائياً'),
            onPressed: () => _confirmDelete(context),
          ),
          const SizedBox(height: 20),
          Center(child: Text('رشاقة • نسخة $_version', style: const TextStyle(color: AppColors.textMuted))),
          const Center(child: Text('أداة توعية وليست بديلاً عن استشارة طبية', style: TextStyle(color: AppColors.textMuted, fontSize: 12))),
        ],
      ),
    );
  }

  Future<void> _editEmail(BuildContext context) async {
    final app = context.read<AppState>();
    final ctrl = TextEditingController(text: app.email ?? '');
    final email = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(app.email == null ? 'إضافة البريد' : 'تغيير البريد'),
        content: TextField(
          controller: ctrl,
          keyboardType: TextInputType.emailAddress,
          autofocus: true,
          decoration: const InputDecoration(
            labelText: 'البريد الإلكتروني',
            hintText: 'example@mail.com',
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('إلغاء')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, ctrl.text.trim()),
            child: const Text('حفظ'),
          ),
        ],
      ),
    );
    if (email == null || email.isEmpty) return;
    if (!email.contains('@') || !email.contains('.')) {
      if (!context.mounted) return;
      showSnack(context, 'البريد الإلكتروني مش مظبوط', error: true);
      return;
    }
    try {
      await Api.setEmail(email);
      await app.refreshMe();
    } catch (e) {
      if (!context.mounted) return;
      showSnack(context, ApiClient.errorMessage(e), error: true);
      return;
    }
    if (!context.mounted) return;
    showSnack(context, 'تم حفظ البريد الإلكتروني ✅');
  }

  Future<void> _restorePurchases(BuildContext context) async {
    final app = context.read<AppState>();
    setState(() => _restoring = true);
    try {
      await Api.billingStatus();
      await app.refreshPremium();
    } catch (e) {
      if (!context.mounted) return;
      showSnack(context, ApiClient.errorMessage(e), error: true);
      return;
    } finally {
      if (mounted) setState(() => _restoring = false);
    }
    if (!context.mounted) return;
    showSnack(context,
        app.isPremium ? 'اشتراكك Premium شغّال ✅' : 'مفيش اشتراك Premium على الحساب ده');
  }

  Future<void> _confirmLogout(BuildContext context) async {
    final app = context.read<AppState>();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('تأكيد الخروج'),
        content: const Text('متأكد إنك عايز تسجّل الخروج؟'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('إلغاء')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: TextButton.styleFrom(foregroundColor: AppColors.danger),
            child: const Text('تسجيل الخروج'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    await app.logout();
  }

  Future<void> _confirmDelete(BuildContext context) async {
    final app = context.read<AppState>();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('حذف الحساب'),
        content: const Text(
            'هتمسح حسابك وكل بياناتك نهائياً (الأكل، الوزن، الوصفات…). الإجراء ده لا يمكن التراجع عنه. متأكد؟'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('إلغاء')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: TextButton.styleFrom(foregroundColor: AppColors.danger),
            child: const Text('حذف نهائي'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await Api.deleteAccount();
    } catch (e) {
      if (mounted) showSnack(context, ApiClient.errorMessage(e), error: true);
      return;
    }
    await app.logout();
  }

  Widget _info(String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Text(k, style: const TextStyle(color: AppColors.textMuted)),
          Text(v, style: const TextStyle(fontWeight: FontWeight.bold)),
        ]),
      );
}

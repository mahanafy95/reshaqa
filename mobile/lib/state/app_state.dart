import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/api_client.dart';
import '../services/api.dart';
import '../services/widget_service.dart';

enum AuthStatus { unknown, unauthenticated, needsProfile, ready }

/// الحالة المركزية: المصادقة، الملف الشخصي، وملخص اليوم.
class AppState extends ChangeNotifier {
  AuthStatus status = AuthStatus.unknown;
  Map<String, dynamic>? profile;
  Map<String, dynamic>? summary;
  Map<String, dynamic>? targets;
  Map<String, dynamic>? water;
  List<dynamic> todayFoods = [];
  bool isPremium = false;
  bool busy = false;
  ThemeMode themeMode = ThemeMode.system;
  static const _kThemeMode = 'theme_mode';

  // هوية المستخدم الحالي (من /auth/me) — للعرض في الإعدادات وربط البريد.
  int? userId;
  String? username;
  String? email;

  bool _unauthHooked = false;

  /// يربط الخروج التلقائي عند انتهاء/إلغاء الجلسة (401 من اعتراض Dio).
  void _hookUnauthorized() {
    if (_unauthHooked) return;
    _unauthHooked = true;
    ApiClient.onUnauthorized = () {
      if (status == AuthStatus.unauthenticated) return; // يمنع التكرار
      logout();
    };
  }

  /// يخزّن بيانات المستخدم من رد /auth/me.
  void _applyMe(Map<String, dynamic> me) {
    isPremium = me['is_premium'] == true;
    userId = (me['id'] as num?)?.toInt();
    username = me['username'] as String?;
    email = me['email'] as String?;
  }

  /// يحمّل وضع الثيم المحفوظ (نظام/فاتح/داكن).
  Future<void> _loadThemeMode() async {
    try {
      final v = (await SharedPreferences.getInstance()).getString(_kThemeMode);
      themeMode = v == 'light'
          ? ThemeMode.light
          : v == 'dark'
              ? ThemeMode.dark
              : ThemeMode.system;
    } catch (_) {/* الافتراضي: نظام */}
  }

  /// يغيّر وضع الثيم ويحفظه.
  Future<void> setThemeMode(ThemeMode mode) async {
    themeMode = mode;
    notifyListeners();
    try {
      final v = mode == ThemeMode.light ? 'light' : mode == ThemeMode.dark ? 'dark' : 'system';
      await (await SharedPreferences.getInstance()).setString(_kThemeMode, v);
    } catch (_) {/* تجاهل */}
  }

  Future<void> bootstrap() async {
    _hookUnauthorized();
    await _loadThemeMode();
    final token = await ApiClient.instance.getToken();
    if (token == null || token.isEmpty) {
      status = AuthStatus.unauthenticated;
      notifyListeners();
      return;
    }
    try {
      _applyMe(await Api.me());
      profile = await Api.getProfile();
      status = profile == null ? AuthStatus.needsProfile : AuthStatus.ready;
      if (status == AuthStatus.ready) await refreshHome();
    } catch (_) {
      await ApiClient.instance.clearToken();
      status = AuthStatus.unauthenticated;
    }
    notifyListeners();
  }

  /// يحدّث حالة الاشتراك (بعد شراء/استعادة).
  Future<void> refreshPremium() async {
    try {
      _applyMe(await Api.me());
      notifyListeners();
    } catch (_) {/* تجاهل */}
  }

  /// يعيد تحميل بيانات المستخدم (بعد إضافة/تغيير البريد مثلاً).
  Future<void> refreshMe() async {
    try {
      _applyMe(await Api.me());
      notifyListeners();
    } catch (_) {/* تجاهل */}
  }

  Future<void> login(String u, String p) async {
    _hookUnauthorized();
    await Api.login(u, p);
    _applyMe(await Api.me());
    profile = await Api.getProfile();
    status = profile == null ? AuthStatus.needsProfile : AuthStatus.ready;
    if (status == AuthStatus.ready) await refreshHome();
    notifyListeners();
  }

  Future<void> register(String u, String p, {String? email}) async {
    _hookUnauthorized();
    await Api.register(u, p, email: email);
    try {
      _applyMe(await Api.me());
    } catch (_) {/* تجاهل */}
    status = AuthStatus.needsProfile;
    notifyListeners();
  }

  Future<void> googleLogin(String idToken) async {
    _hookUnauthorized();
    await Api.googleLogin(idToken);
    _applyMe(await Api.me());
    profile = await Api.getProfile();
    status = profile == null ? AuthStatus.needsProfile : AuthStatus.ready;
    if (status == AuthStatus.ready) await refreshHome();
    notifyListeners();
  }

  Future<void> saveProfile(Map<String, dynamic> body) async {
    profile = await Api.saveProfile(body);
    status = AuthStatus.ready;
    await refreshHome();
    notifyListeners();
  }

  Future<void> refreshHome() async {
    try {
      final today = DateTime.now().toIso8601String().split('T').first;
      final results = await Future.wait([
        Api.summary(today),
        Api.targets(),
        Api.water(today),
      ]);
      summary = results[0];
      targets = results[1];
      water = results[2];
      todayFoods = await Api.foods(today);
      _syncWidget();
    } catch (_) {
      // نتجاهل أخطاء التحديث الخفيفة
    }
    notifyListeners();
  }

  void _syncWidget() {
    final s = summary;
    if (s == null) return;
    WidgetService.update(
      remaining: (s['remaining_calories'] as num?)?.round() ?? 0,
      target: (s['target_calories'] as num?)?.round() ?? 0,
      eaten: (s['eaten_calories'] as num?)?.round() ?? 0,
    );
  }

  Future<void> logout() async {
    await ApiClient.instance.clearToken();
    profile = null;
    summary = null;
    targets = null;
    water = null;
    isPremium = false;
    userId = null;
    username = null;
    email = null;
    status = AuthStatus.unauthenticated;
    notifyListeners();
  }
}

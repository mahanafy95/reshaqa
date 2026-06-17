import 'package:flutter/foundation.dart';

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
  bool busy = false;

  Future<void> bootstrap() async {
    final token = await ApiClient.instance.getToken();
    if (token == null || token.isEmpty) {
      status = AuthStatus.unauthenticated;
      notifyListeners();
      return;
    }
    try {
      await Api.me();
      profile = await Api.getProfile();
      status = profile == null ? AuthStatus.needsProfile : AuthStatus.ready;
      if (status == AuthStatus.ready) await refreshHome();
    } catch (_) {
      await ApiClient.instance.clearToken();
      status = AuthStatus.unauthenticated;
    }
    notifyListeners();
  }

  Future<void> login(String u, String p) async {
    await Api.login(u, p);
    profile = await Api.getProfile();
    status = profile == null ? AuthStatus.needsProfile : AuthStatus.ready;
    if (status == AuthStatus.ready) await refreshHome();
    notifyListeners();
  }

  Future<void> register(String u, String p) async {
    await Api.register(u, p);
    status = AuthStatus.needsProfile;
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
    status = AuthStatus.unauthenticated;
    notifyListeners();
  }
}

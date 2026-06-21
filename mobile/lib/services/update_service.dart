import 'package:package_info_plus/package_info_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';

import '../core/api_client.dart';
import 'api.dart';

class UpdateInfo {
  UpdateInfo({
    required this.versionCode,
    required this.versionName,
    required this.notes,
    required this.mandatory,
    required this.downloadUrl,
  });
  final int versionCode;
  final String versionName;
  final String notes;
  final bool mandatory;
  final String downloadUrl;
}

/// التحديث الذاتي.
///
/// أغلب التحديثات بتوصل **بصمت** عبر Shorebird (تعديلات Dart تتطبّق عند فتح التطبيق
/// بدون إعادة تثبيت ولا إشعار). البانر ده بيظهر بس للتحديثات اللي محتاجة APK جديد
/// (تغييرات native/مكتبات) — ويفضّل المستخدم يقدر يخفيه، فبنفتكر النسخة اللي خفّاها.
class UpdateService {
  static const _dismissedKey = 'dismissed_update_code';

  static Future<UpdateInfo?> check() async {
    try {
      final info = await PackageInfo.fromPlatform();
      final current = int.tryParse(info.buildNumber) ?? 0;
      final v = await Api.appVersion();
      final serverCode = (v['version_code'] as num?)?.toInt() ?? 0;
      final available = v['apk_available'] == true;
      if (available && serverCode > current) {
        final mandatory = v['mandatory'] == true;
        // لو المستخدم خفّى نفس النسخة دي قبل كده (وهي مش إجبارية) منعرضهاش تاني.
        if (!mandatory && await _isDismissed(serverCode)) return null;
        // رابط التنزيل قد يكون مطلقاً (GitHub Release) أو مساراً نسبياً على الخادم
        final raw = (v['download_url'] ?? '/app/download').toString();
        final url = raw.startsWith('http') ? raw : '$kApiBaseUrl$raw';
        return UpdateInfo(
          versionCode: serverCode,
          versionName: v['version_name']?.toString() ?? '',
          notes: v['notes_ar']?.toString() ?? '',
          mandatory: mandatory,
          downloadUrl: url,
        );
      }
    } catch (_) {
      // فحص التحديث اختياري — نتجاهل أي خطأ
    }
    return null;
  }

  static Future<bool> _isDismissed(int code) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      return prefs.getInt(_dismissedKey) == code;
    } catch (_) {
      return false;
    }
  }

  /// يخفي بانر النسخة دي (لحد ما تنزل نسخة أحدث منها).
  static Future<void> dismiss(int code) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setInt(_dismissedKey, code);
    } catch (_) {/* تجاهل */}
  }

  static Future<void> openDownload(String url) async {
    final uri = Uri.parse(url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }
}

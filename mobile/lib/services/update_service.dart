import 'package:package_info_plus/package_info_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import 'api.dart';

class UpdateInfo {
  UpdateInfo({required this.versionName, required this.notes, required this.mandatory});
  final String versionName;
  final String notes;
  final bool mandatory;
}

/// التحديث الذاتي: يقارن نسخة التطبيق بنسخة الخادم، ويفتح رابط التنزيل عند الموافقة.
class UpdateService {
  /// يُرجع معلومات التحديث لو فيه نسخة أحدث متاحة، وإلا null.
  static Future<UpdateInfo?> check() async {
    try {
      final info = await PackageInfo.fromPlatform();
      final current = int.tryParse(info.buildNumber) ?? 0;
      final v = await Api.appVersion();
      final serverCode = (v['version_code'] as num?)?.toInt() ?? 0;
      final available = v['apk_available'] == true;
      if (available && serverCode > current) {
        return UpdateInfo(
          versionName: v['version_name']?.toString() ?? '',
          notes: v['notes_ar']?.toString() ?? '',
          mandatory: v['mandatory'] == true,
        );
      }
    } catch (_) {
      // فحص التحديث اختياري — نتجاهل أي خطأ
    }
    return null;
  }

  /// يفتح رابط تنزيل آخر APK في المتصفح (ينزّله ثم يثبّته المستخدم).
  static Future<void> openDownload() async {
    final uri = Uri.parse(Api.downloadUrl);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }
}

import 'package:package_info_plus/package_info_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import '../core/api_client.dart';
import 'api.dart';

class UpdateInfo {
  UpdateInfo({
    required this.versionName,
    required this.notes,
    required this.mandatory,
    required this.downloadUrl,
  });
  final String versionName;
  final String notes;
  final bool mandatory;
  final String downloadUrl;
}

/// التحديث الذاتي: يقارن نسخة التطبيق بنسخة الخادم، ويفتح رابط التنزيل عند الموافقة.
class UpdateService {
  static Future<UpdateInfo?> check() async {
    try {
      final info = await PackageInfo.fromPlatform();
      final current = int.tryParse(info.buildNumber) ?? 0;
      final v = await Api.appVersion();
      final serverCode = (v['version_code'] as num?)?.toInt() ?? 0;
      final available = v['apk_available'] == true;
      if (available && serverCode > current) {
        // رابط التنزيل قد يكون مطلقاً (GitHub Release) أو مساراً نسبياً على الخادم
        final raw = (v['download_url'] ?? '/app/download').toString();
        final url = raw.startsWith('http') ? raw : '$kApiBaseUrl$raw';
        return UpdateInfo(
          versionName: v['version_name']?.toString() ?? '',
          notes: v['notes_ar']?.toString() ?? '',
          mandatory: v['mandatory'] == true,
          downloadUrl: url,
        );
      }
    } catch (_) {
      // فحص التحديث اختياري — نتجاهل أي خطأ
    }
    return null;
  }

  static Future<void> openDownload(String url) async {
    final uri = Uri.parse(url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }
}

import 'package:google_sign_in/google_sign_in.dart';

import '../core/api_client.dart';

/// غلاف بسيط لتسجيل الدخول بجوجل — يُرجع ID token لإرساله للباك-إند.
///
/// المعرّف (معرّف عميل الويب) يُحدَّد إمّا وقت البناء (dart-define) أو وقت التشغيل
/// من /auth/config، فيتفعّل الزر بمجرّد ضبط الخادم من غير إعادة بناء التطبيق.
/// نمرّره كـ serverClientId فيخرج idToken جمهوره (aud) هو نفس المعرّف اللي
/// الباك-إند بيتحقّق منه.
class GoogleSignInService {
  static String _clientId = kGoogleServerClientId; // قيمة البناء كاحتياطي
  static GoogleSignIn? _google;

  /// يضبط المعرّف وقت التشغيل (من إعدادات الخادم). يعيد إنشاء العميل لو تغيّر.
  static void configure(String clientId) {
    final c = clientId.trim();
    if (c.isNotEmpty && c != _clientId) {
      _clientId = c;
      _google = null;
    }
  }

  static bool get configured => _clientId.isNotEmpty;

  static GoogleSignIn get _instance => _google ??= GoogleSignIn(
        scopes: const ['email'],
        serverClientId: _clientId.isEmpty ? null : _clientId,
      );

  /// يبدأ تدفّق جوجل ويُرجع ID token، أو null لو المستخدم ألغى أو ما فيش توكن.
  static Future<String?> signIn() async {
    // نسجّل خروج أولاً ليظهر اختيار الحساب في كل مرة (تجربة أوضح)
    try {
      await _instance.signOut();
    } catch (_) {/* تجاهل */}
    final account = await _instance.signIn();
    if (account == null) return null; // المستخدم ألغى
    final auth = await account.authentication;
    return auth.idToken;
  }
}

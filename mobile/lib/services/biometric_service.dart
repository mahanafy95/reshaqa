import 'package:local_auth/local_auth.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// قفل بيومتري/PIN للتطبيق.
class BiometricService {
  static final _auth = LocalAuthentication();
  static const _kLockEnabled = 'reshaqa_lock_enabled';

  static Future<bool> isLockEnabled() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_kLockEnabled) ?? false;
  }

  static Future<void> setLockEnabled(bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kLockEnabled, value);
  }

  static Future<bool> canCheck() async {
    try {
      return await _auth.isDeviceSupported();
    } catch (_) {
      return false;
    }
  }

  static Future<bool> authenticate() async {
    try {
      return await _auth.authenticate(
        localizedReason: 'افتح رشاقة ببصمتك أو رقمك السري',
        options: const AuthenticationOptions(
          biometricOnly: false, // يسمح بـ PIN/نمط الجهاز كبديل
          stickyAuth: true,
        ),
      );
    } catch (_) {
      return false;
    }
  }
}

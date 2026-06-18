import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// عنوان الـ backend — الافتراضي هو السيرفر السحابي (الإنتاج).
/// للتطوير المحلي مرّر: --dart-define=API_BASE_URL=http://10.0.2.2:8000
const String kApiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'https://reshaqa-backend.onrender.com',
);

/// معرّف عميل الويب من Google Cloud (نفس قيمة GOOGLE_CLIENT_IDS بالباك-إند).
/// يُمرَّر وقت البناء: --dart-define=GOOGLE_SERVER_CLIENT_ID=xxxx.apps.googleusercontent.com
/// لو فاضي، زر "الدخول بجوجل" يختفي تلقائياً ويبقى الدخول بكلمة السر شغّال.
const String kGoogleServerClientId = String.fromEnvironment(
  'GOOGLE_SERVER_CLIENT_ID',
  defaultValue: '',
);

/// عميل HTTP مع حقن توكن JWT تلقائياً وتخزينه بأمان.
class ApiClient {
  ApiClient._() {
    _dio = Dio(BaseOptions(
      baseUrl: kApiBaseUrl,
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 20),
      headers: {'Content-Type': 'application/json'},
    ));
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await _storage.read(key: _kToken);
        if (token != null && token.isNotEmpty) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
      onError: (err, handler) async {
        // 401 على نقطة مش تسجيل دخول = التوكن انتهى/اتلغى → خروج تلقائي.
        // (نستثني login/register/google/reset عشان "باسورد غلط" مش معناه انتهاء جلسة.)
        if (err.response?.statusCode == 401 && !_isAuthAttempt(err.requestOptions.path)) {
          await clearToken();
          onUnauthorized?.call();
        }
        handler.next(err);
      },
    ));
  }

  /// يُستدعى لما تنتهي/تُلغى جلسة وسط الاستخدام — يربطه AppState بـ logout().
  static void Function()? onUnauthorized;

  static bool _isAuthAttempt(String path) =>
      path.contains('/auth/login') ||
      path.contains('/auth/register') ||
      path.contains('/auth/token') ||
      path.contains('/auth/google') ||
      path.contains('/auth/forgot-password') ||
      path.contains('/auth/reset-password');

  static final ApiClient instance = ApiClient._();

  late final Dio _dio;
  final _storage = const FlutterSecureStorage();
  static const _kToken = 'reshaqa_token';

  Dio get dio => _dio;

  Future<void> saveToken(String token) => _storage.write(key: _kToken, value: token);
  Future<String?> getToken() => _storage.read(key: _kToken);
  Future<void> clearToken() => _storage.delete(key: _kToken);

  /// كود حالة HTTP من خطأ Dio (أو null لو مش خطأ شبكة).
  static int? statusOf(Object e) => e is DioException ? e.response?.statusCode : null;

  /// يحوّل أخطاء Dio إلى رسالة عربية ودّية.
  static String errorMessage(Object e) {
    if (e is DioException) {
      final data = e.response?.data;
      if (data is Map && data['detail'] != null) {
        final detail = data['detail'];
        if (detail is String) return detail;
        if (detail is Map && detail['message'] != null) return detail['message'].toString();
        if (detail is List && detail.isNotEmpty) {
          final first = detail.first;
          if (first is Map && first['msg'] != null) return first['msg'].toString();
        }
      }
      if (e.type == DioExceptionType.connectionError ||
          e.type == DioExceptionType.connectionTimeout) {
        return 'تعذّر الاتصال بالخادم. تأكد من الإنترنت وحاول تاني.';
      }
    }
    return 'حصل خطأ غير متوقع. حاول تاني.';
  }
}

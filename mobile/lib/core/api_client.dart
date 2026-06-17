import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// عنوان الـ backend — يُمرَّر عبر --dart-define=API_BASE_URL=...
/// الافتراضي 10.0.2.2 = localhost من محاكي أندرويد.
const String kApiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://10.0.2.2:8000',
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
    ));
  }

  static final ApiClient instance = ApiClient._();

  late final Dio _dio;
  final _storage = const FlutterSecureStorage();
  static const _kToken = 'reshaqa_token';

  Dio get dio => _dio;

  Future<void> saveToken(String token) => _storage.write(key: _kToken, value: token);
  Future<String?> getToken() => _storage.read(key: _kToken);
  Future<void> clearToken() => _storage.delete(key: _kToken);

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

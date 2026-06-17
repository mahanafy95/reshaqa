import 'package:dio/dio.dart';

import '../core/api_client.dart';

/// كل استدعاءات الـ backend مجمّعة. تُرجع JSON مفكوك (Map/List).
class Api {
  static final Dio _d = ApiClient.instance.dio;

  // ---------- المصادقة ----------
  static Future<String> register(String username, String password) async {
    final r = await _d.post('/auth/register', data: {'username': username, 'password': password});
    final token = r.data['access_token'] as String;
    await ApiClient.instance.saveToken(token);
    return token;
  }

  static Future<String> login(String username, String password) async {
    final r = await _d.post('/auth/login', data: {'username': username, 'password': password});
    final token = r.data['access_token'] as String;
    await ApiClient.instance.saveToken(token);
    return token;
  }

  static Future<Map<String, dynamic>> me() async => (await _d.get('/auth/me')).data;

  // ---------- الملف الشخصي ----------
  static Future<Map<String, dynamic>?> getProfile() async {
    try {
      return (await _d.get('/profile')).data;
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) return null;
      rethrow;
    }
  }

  static Future<Map<String, dynamic>> saveProfile(Map<String, dynamic> body) async =>
      (await _d.put('/profile', data: body)).data;

  // ---------- الأهداف والملخص ----------
  static Future<Map<String, dynamic>> targets() async => (await _d.get('/targets')).data;
  static Future<Map<String, dynamic>> saveTodayTarget() async => (await _d.post('/targets/today')).data;
  static Future<Map<String, dynamic>> summary([String? on]) async =>
      (await _d.get('/summary', queryParameters: on != null ? {'on': on} : null)).data;
  static Future<Map<String, dynamic>> bodyMetrics() async => (await _d.get('/metrics/body')).data;
  static Future<List<dynamic>> drinkSuggestions() async => (await _d.get('/drinks/suggestions')).data;

  // ---------- تسجيل الأكل ----------
  static Future<List<dynamic>> foods(String on) async =>
      (await _d.get('/foods', queryParameters: {'on': on})).data;
  static Future<Map<String, dynamic>> addFood(Map<String, dynamic> body) async =>
      (await _d.post('/foods', data: body)).data;
  static Future<Map<String, dynamic>> updateFood(int id, Map<String, dynamic> body) async =>
      (await _d.put('/foods/$id', data: body)).data;
  static Future<void> deleteFood(int id) async => await _d.delete('/foods/$id');

  static Future<List<dynamic>> librarySearch(String q, {String? region}) async =>
      (await _d.get('/foods/library/search', queryParameters: {'q': q, if (region != null) 'region': region})).data;
  static Future<Map<String, dynamic>> estimate(String name, double amount) async =>
      (await _d.get('/foods/estimate', queryParameters: {'name': name, 'amount': amount})).data;
  static Future<Map<String, dynamic>> barcode(String code) async =>
      (await _d.get('/foods/barcode/$code')).data;
  static Future<Map<String, dynamic>> parseLabel(String text) async {
    final form = FormData.fromMap({'text': text});
    return (await _d.post('/foods/label', data: form)).data;
  }
  static Future<List<dynamic>> suggest(String q) async =>
      (await _d.get('/foods/suggest', queryParameters: {'q': q})).data;
  static Future<Map<String, dynamic>> parseMeal(String text,
      {String? date, String defaultMeal = 'snack', bool confirm = false}) async =>
      (await _d.post('/foods/parse', data: {
        'text': text,
        if (date != null) 'date': date,
        'default_meal': defaultMeal,
        'confirm': confirm,
      })).data;

  // ---------- الوصفات ----------
  static Future<List<dynamic>> recipes() async => (await _d.get('/recipes')).data;
  static Future<Map<String, dynamic>> createRecipe(Map<String, dynamic> body) async =>
      (await _d.post('/recipes', data: body)).data;
  static Future<Map<String, dynamic>> logRecipe(int id, Map<String, dynamic> body) async =>
      (await _d.post('/recipes/$id/log', data: body)).data;
  static Future<void> deleteRecipe(int id) async => await _d.delete('/recipes/$id');

  // ---------- المفضّلة ----------
  static Future<List<dynamic>> favorites() async => (await _d.get('/favorites')).data;
  static Future<Map<String, dynamic>> addFavorite(Map<String, dynamic> body) async =>
      (await _d.post('/favorites', data: body)).data;
  static Future<Map<String, dynamic>> logFavorite(int id, Map<String, dynamic> body) async =>
      (await _d.post('/favorites/$id/log', data: body)).data;
  static Future<void> deleteFavorite(int id) async => await _d.delete('/favorites/$id');

  // ---------- المتابعة ----------
  static Future<Map<String, dynamic>> addWeight(double kg, [String? date]) async =>
      (await _d.post('/weight', data: {'weight_kg': kg, if (date != null) 'date': date})).data;
  static Future<List<dynamic>> weights() async => (await _d.get('/weight')).data;
  static Future<Map<String, dynamic>> weightTrend() async => (await _d.get('/weight/trend')).data;
  static Future<Map<String, dynamic>> addWaist(double cm) async =>
      (await _d.post('/waist', data: {'waist_cm': cm})).data;
  static Future<Map<String, dynamic>> addWater(int ml) async =>
      (await _d.post('/water', data: {'ml': ml})).data;
  static Future<Map<String, dynamic>> water([String? on]) async =>
      (await _d.get('/water', queryParameters: on != null ? {'on': on} : null)).data;
  static Future<Map<String, dynamic>> addActivity(Map<String, dynamic> body) async =>
      (await _d.post('/activity', data: body)).data;
  static Future<List<dynamic>> activities(String on) async =>
      (await _d.get('/activity', queryParameters: {'on': on})).data;
  static Future<void> deleteActivity(int id) async => await _d.delete('/activity/$id');
  static Future<Map<String, dynamic>> saveMood(Map<String, dynamic> body) async =>
      (await _d.put('/mood', data: body)).data;
  static Future<Map<String, dynamic>?> mood([String? on]) async {
    final r = await _d.get('/mood', queryParameters: on != null ? {'on': on} : null);
    return r.data == null ? null : Map<String, dynamic>.from(r.data);
  }

  // ---------- مزامنة الصحة ----------
  static Future<Map<String, dynamic>> healthSync(Map<String, dynamic> body) async =>
      (await _d.post('/health/sync', data: body)).data;
  static Future<Map<String, dynamic>> healthStatus() async => (await _d.get('/health/status')).data;

  // ---------- التحديث الذاتي ----------
  static Future<Map<String, dynamic>> appVersion() async => (await _d.get('/app/version')).data;
  static String get downloadUrl => '$kApiBaseUrl/app/download';

  // ---------- التقارير ----------
  static Future<Map<String, dynamic>> weeklyReport([String? weekOf]) async =>
      (await _d.get('/reports/weekly', queryParameters: weekOf != null ? {'week_of': weekOf} : null)).data;
  static Future<Map<String, dynamic>> monthlyReport(int year, int month) async =>
      (await _d.get('/reports/monthly', queryParameters: {'year': year, 'month': month})).data;

  /// يحمّل تقرير PDF كـ bytes (للحفظ/المشاركة).
  static Future<List<int>> weeklyPdf([String? weekOf]) async {
    final r = await _d.get<List<int>>('/reports/weekly.pdf',
        queryParameters: weekOf != null ? {'week_of': weekOf} : null,
        options: Options(responseType: ResponseType.bytes));
    return r.data!;
  }

  static Future<List<int>> monthlyPdf(int year, int month) async {
    final r = await _d.get<List<int>>('/reports/monthly.pdf',
        queryParameters: {'year': year, 'month': month},
        options: Options(responseType: ResponseType.bytes));
    return r.data!;
  }
}

import 'package:dio/dio.dart';

import '../core/api_client.dart';

/// كل استدعاءات الـ backend مجمّعة. تُرجع JSON مفكوك (Map/List).
class Api {
  static final Dio _d = ApiClient.instance.dio;

  /// مهلة استقبال أطول للنداءات اللي بتمرّ على الذكاء الاصطناعي (محادثة/تحليل أكل/تصوير).
  /// الـ LLM ممكن ياخد وقت في توليد الرد (وأحياناً بنرجع لمزوّد احتياطي)، فالمهلة
  /// الافتراضية (20ث) كانت بتقطع وتطلّع «خطأ غير متوقع». 90ث تغطّي الحالات البطيئة.
  static final Options _aiOpts = Options(receiveTimeout: const Duration(seconds: 90));

  // ---------- المصادقة ----------
  static Future<String> register(String username, String password, {String? email}) async {
    final r = await _d.post('/auth/register', data: {
      'username': username,
      'password': password,
      if (email != null && email.isNotEmpty) 'email': email,
    });
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

  static Future<String> googleLogin(String idToken) async {
    final r = await _d.post('/auth/google', data: {'id_token': idToken});
    final token = r.data['access_token'] as String;
    await ApiClient.instance.saveToken(token);
    return token;
  }

  static Future<Map<String, dynamic>> me() async => (await _d.get('/auth/me')).data;
  static Future<Map<String, dynamic>> authConfig() async => (await _d.get('/auth/config')).data;
  static Future<void> deleteAccount() async => await _d.delete('/auth/account');

  // ---------- المجتمع (أصدقاء + رسائل) ----------
  static Future<List<dynamic>> searchUsers(String q) async =>
      (await _d.get('/social/search', queryParameters: {'q': q})).data;
  static Future<Map<String, dynamic>> friends() async => (await _d.get('/social/friends')).data;
  static Future<Map<String, dynamic>> friendRequest(int userId) async =>
      (await _d.post('/social/friends/request/$userId')).data;
  static Future<Map<String, dynamic>> acceptFriend(int userId) async =>
      (await _d.post('/social/friends/$userId/accept')).data;
  static Future<Map<String, dynamic>> removeFriend(int userId) async =>
      (await _d.delete('/social/friends/$userId')).data;
  static Future<List<dynamic>> messages(int userId, {int afterId = 0}) async =>
      (await _d.get('/social/messages/$userId', queryParameters: {'after_id': afterId})).data;
  static Future<Map<String, dynamic>> sendMessage(int toUserId, String body) async =>
      (await _d.post('/social/messages', data: {'to_user_id': toUserId, 'body': body})).data;
  static Future<Map<String, dynamic>> cheer(int userId) async =>
      (await _d.post('/social/cheer/$userId')).data;
  static Future<int> unread() async =>
      ((await _d.get('/social/unread')).data['total'] as num).toInt();

  // ---------- الاشتراكات (Google Play) ----------
  static Future<Map<String, dynamic>> billingStatus() async =>
      (await _d.get('/billing/status')).data;
  static Future<Map<String, dynamic>> verifyPurchase(String productId, String purchaseToken) async =>
      (await _d.post('/billing/google/verify',
              data: {'product_id': productId, 'purchase_token': purchaseToken}))
          .data;

  // ---------- استرجاع كلمة السر بالبريد ----------
  static Future<Map<String, dynamic>> setEmail(String email) async =>
      (await _d.post('/auth/email', data: {'email': email})).data;
  static Future<Map<String, dynamic>> forgotPassword(String email) async =>
      (await _d.post('/auth/forgot-password', data: {'email': email})).data;
  static Future<String> resetPassword(String email, String code, String newPassword) async {
    final r = await _d.post('/auth/reset-password',
        data: {'email': email, 'code': code, 'new_password': newPassword});
    final token = r.data['access_token'] as String;
    await ApiClient.instance.saveToken(token);
    return token;
  }

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
  /// سلسلة أيام التسجيل المتتالية + الإنجازات (للتحفيز على الرئيسية).
  static Future<Map<String, dynamic>> streak({String? on}) async =>
      (await _d.get('/streak', queryParameters: {if (on != null) 'on': on})).data;

  /// تصدير كل بيانات المستخدم كـ CSV (bytes) — للمشاركة/الحفظ.
  static Future<List<int>> exportData() async {
    final r = await _d.get('/export',
        options: Options(responseType: ResponseType.bytes, receiveTimeout: const Duration(seconds: 60)));
    return (r.data as List).cast<int>();
  }
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
      (await _d.get('/foods/estimate',
              queryParameters: {'name': name, 'amount': amount}, options: _aiOpts))
          .data;
  static Future<Map<String, dynamic>> barcode(String code) async =>
      (await _d.get('/foods/barcode/$code', options: _aiOpts)).data;
  static Future<Map<String, dynamic>> saveBarcode(Map<String, dynamic> body) async =>
      (await _d.post('/foods/barcode', data: body)).data;
  static Future<Map<String, dynamic>> parseLabel(String text) async {
    final form = FormData.fromMap({'text': text});
    return (await _d.post('/foods/label', data: form)).data;
  }

  /// يرفع صورة الملصق الغذائي ويقراها بالذكاء الاصطناعي (عربي/إنجليزي).
  /// يرجّع نفس شكل /foods/label (سعرات/بروتين/نشويات/دهون لكل 100جم).
  static Future<Map<String, dynamic>> labelImage(String filePath) async {
    final form = FormData.fromMap({
      'file': await MultipartFile.fromFile(filePath, filename: 'label.jpg'),
    });
    return (await _d.post('/foods/label-image', data: form, options: _aiOpts)).data;
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
      }, options: _aiOpts)).data;

  // ---------- الوصفات ----------
  static Future<List<dynamic>> recipes() async => (await _d.get('/recipes')).data;
  static Future<Map<String, dynamic>> createRecipe(Map<String, dynamic> body) async =>
      (await _d.post('/recipes', data: body)).data;
  static Future<Map<String, dynamic>> updateRecipe(int id, Map<String, dynamic> body) async =>
      (await _d.put('/recipes/$id', data: body)).data;
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
  /// توقّع زمن الوصول لوزن الهدف بناءً على اتجاه القياسات.
  static Future<Map<String, dynamic>> weightForecast() async => (await _d.get('/weight/forecast')).data;
  static Future<Map<String, dynamic>> addWaist(double cm) async =>
      (await _d.post('/waist', data: {'waist_cm': cm})).data;
  static Future<List<dynamic>> waists() async => (await _d.get('/waist')).data;
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

  // ---------- المساعد الذكي ----------
  /// محادثة المساعد. [date] = تاريخ اليوم المحلي (لتسجيل وجبة لو المستخدم قال «ضيف/سجّل»).
  /// الرد ممكن يحتوي على logged/logged_items لو اتسجّلت وجبة.
  static Future<Map<String, dynamic>> assistantChat(
    List<Map<String, String>> messages, {
    String? date,
    String? defaultMeal,
  }) async =>
      (await _d.post('/assistant/chat', data: {
        'messages': messages,
        if (date != null) 'date': date,
        if (defaultMeal != null) 'default_meal': defaultMeal,
      }, options: _aiOpts)).data;

  /// يرجّع محادثة المستخدم المحفوظة (لاستعادتها عند فتح الشاشة).
  static Future<List<dynamic>> assistantHistory({int limit = 100}) async =>
      ((await _d.get('/assistant/history', queryParameters: {'limit': limit})).data['messages']
          as List<dynamic>);

  /// يمسح محادثة المستخدم مع المساعد.
  static Future<void> clearAssistantHistory() async => await _d.delete('/assistant/history');

  // ---------- الإبلاغ عن مشكلة ----------
  static Future<Map<String, dynamic>> reportIssue(String message, {String? context}) async =>
      (await _d.post('/issues', data: {'message': message, if (context != null) 'context': context})).data;
  static Future<List<dynamic>> issues() async => (await _d.get('/issues')).data;
  static Future<Map<String, dynamic>> updateIssueStatus(int id, String status) async =>
      (await _d.patch('/issues/$id', data: {'status': status})).data;

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

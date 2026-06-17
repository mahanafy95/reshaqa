import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_timezone/flutter_timezone.dart';
import 'package:timezone/data/latest_all.dart' as tzdata;
import 'package:timezone/timezone.dart' as tz;

/// خدمة الإشعارات والمنبّهات.
/// منبّه المياه يطلع صوت حتى لو الموبايل صامت (قناة بصوت منبّه + full-screen intent + exact alarm).
class NotificationsService {
  static final _plugin = FlutterLocalNotificationsPlugin();
  static bool _inited = false;

  // قناة المياه: تنبيه قوي بصوت منبّه (alarm usage) يتجاوز الصامت
  static const _waterChannel = AndroidNotificationChannel(
    'reshaqa_water_alarm',
    'تنبيه شرب المياه',
    description: 'منبّه شرب المياه بصوت حتى في الوضع الصامت',
    importance: Importance.max,
    playSound: true,
    audioAttributesUsage: AudioAttributesUsage.alarm,
  );

  static const _mealChannel = AndroidNotificationChannel(
    'reshaqa_meal',
    'تذكير تسجيل الأكل',
    description: 'تذكير بتسجيل وجباتك',
    importance: Importance.high,
  );

  static const _weighChannel = AndroidNotificationChannel(
    'reshaqa_weigh',
    'تذكير الوزن',
    description: 'تذكير وزن الجمعة الصباحي',
    importance: Importance.high,
  );

  static Future<void> init() async {
    if (_inited) return;
    tzdata.initializeTimeZones();
    try {
      final name = await FlutterTimezone.getLocalTimezone();
      tz.setLocalLocation(tz.getLocation(name));
    } catch (_) {
      tz.setLocalLocation(tz.getLocation('Asia/Riyadh'));
    }

    const initSettings = InitializationSettings(
      android: AndroidInitializationSettings('@mipmap/ic_launcher'),
    );
    await _plugin.initialize(initSettings);

    final android = _plugin.resolvePlatformSpecificImplementation<
        AndroidFlutterLocalNotificationsPlugin>();
    await android?.createNotificationChannel(_waterChannel);
    await android?.createNotificationChannel(_mealChannel);
    await android?.createNotificationChannel(_weighChannel);
    _inited = true;
  }

  static Future<void> requestPermissions() async {
    final android = _plugin.resolvePlatformSpecificImplementation<
        AndroidFlutterLocalNotificationsPlugin>();
    await android?.requestNotificationsPermission();
    await android?.requestExactAlarmsPermission();
  }

  static tz.TZDateTime _nextTime(int hour, int minute) {
    final now = tz.TZDateTime.now(tz.local);
    var t = tz.TZDateTime(tz.local, now.year, now.month, now.day, hour, minute);
    if (t.isBefore(now)) t = t.add(const Duration(days: 1));
    return t;
  }

  static tz.TZDateTime _nextWeekday(int weekday, int hour, int minute) {
    var t = _nextTime(hour, minute);
    while (t.weekday != weekday) {
      t = t.add(const Duration(days: 1));
    }
    return t;
  }

  /// منبّهات المياه عبر اليوم — كل واحد بصوت منبّه و full-screen intent.
  static Future<void> scheduleWaterReminders({List<int> hours = const [10, 12, 14, 16, 18, 20]}) async {
    for (final h in hours) {
      await _plugin.zonedSchedule(
        1000 + h,
        '💧 وقت المياه',
        'اشرب كوباية مياه دلوقتي — جسمك بيشكرك!',
        _nextTime(h, 0),
        NotificationDetails(
          android: AndroidNotificationDetails(
            _waterChannel.id, _waterChannel.name,
            channelDescription: _waterChannel.description,
            importance: Importance.max,
            priority: Priority.high,
            category: AndroidNotificationCategory.alarm,
            fullScreenIntent: true,
            playSound: true,
            audioAttributesUsage: AudioAttributesUsage.alarm,
          ),
        ),
        androidScheduleMode: AndroidScheduleMode.exactAllowWhileIdle,
        uiLocalNotificationDateInterpretation: UILocalNotificationDateInterpretation.absoluteTime,
        matchDateTimeComponents: DateTimeComponents.time,
      );
    }
  }

  /// تذكيرات تسجيل الأكل (فطار/غدا/عشا).
  static Future<void> scheduleMealReminders() async {
    const meals = {2001: [9, 0, 'فطارك'], 2002: [14, 30, 'غداك'], 2003: [20, 30, 'عشاك']};
    for (final e in meals.entries) {
      final h = e.value[0] as int, m = e.value[1] as int, label = e.value[2] as String;
      await _plugin.zonedSchedule(
        e.key, '🍽️ متنساش تسجّل $label', 'سجّل أكلتك عشان نتابع يومك مع بعض 🙂',
        _nextTime(h, m),
        const NotificationDetails(
          android: AndroidNotificationDetails(
            'reshaqa_meal', 'تذكير تسجيل الأكل',
            importance: Importance.high, priority: Priority.high,
          ),
        ),
        androidScheduleMode: AndroidScheduleMode.exactAllowWhileIdle,
        uiLocalNotificationDateInterpretation: UILocalNotificationDateInterpretation.absoluteTime,
        matchDateTimeComponents: DateTimeComponents.time,
      );
    }
  }

  /// تذكير وزن الجمعة الصباحي.
  static Future<void> scheduleFridayWeighIn() async {
    await _plugin.zonedSchedule(
      3001, '⚖️ صباح الخير! وقت وزن الجمعة',
      'اوزن نفسك الصبح على الريق عشان نتابع اتجاه وزنك بدقة 💚',
      _nextWeekday(DateTime.friday, 8, 0),
      const NotificationDetails(
        android: AndroidNotificationDetails(
          'reshaqa_weigh', 'تذكير الوزن',
          importance: Importance.high, priority: Priority.high,
        ),
      ),
      androidScheduleMode: AndroidScheduleMode.exactAllowWhileIdle,
      uiLocalNotificationDateInterpretation: UILocalNotificationDateInterpretation.absoluteTime,
      matchDateTimeComponents: DateTimeComponents.dayOfWeekAndTime,
    );
  }

  static Future<void> scheduleAll() async {
    await scheduleWaterReminders();
    await scheduleMealReminders();
    await scheduleFridayWeighIn();
  }

  static Future<void> cancelAll() => _plugin.cancelAll();
}

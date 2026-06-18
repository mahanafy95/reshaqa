import 'package:home_widget/home_widget.dart';

/// تحديث الـ Home screen widget: المتبقي من السعرات + إضافة سريعة.
class WidgetService {
  static const _widgetName = 'ReshaqaWidgetProvider';

  static Future<void> update({
    required int remaining,
    required int target,
    required int eaten,
  }) async {
    try {
      await HomeWidget.saveWidgetData<int>('remaining', remaining);
      await HomeWidget.saveWidgetData<int>('target', target);
      await HomeWidget.saveWidgetData<int>('eaten', eaten);
      await HomeWidget.saveWidgetData<String>(
        'label',
        remaining >= 0 ? 'باقي $remaining سعرة' : 'زيادة ${-remaining} سعرة',
      );
      await HomeWidget.updateWidget(androidName: _widgetName, qualifiedAndroidName: 'com.reshaqa.reshaqa.$_widgetName');
    } catch (_) {
      // الـ widget اختياري — نتجاهل الفشل بصمت
    }
  }
}

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'app.dart';
import 'services/billing_service.dart';
import 'services/notifications_service.dart';
import 'state/app_state.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  try {
    await NotificationsService.init();
  } catch (_) {}
  final appState = AppState()..bootstrap();
  // مستمع مشتريات Play في الخلفية — يحدّث حالة الاشتراك تلقائياً (تجديد/استعادة)
  BillingService.onEntitlementChanged = appState.refreshPremium;
  try {
    await BillingService.init();
  } catch (_) {}
  runApp(
    ChangeNotifierProvider(
      create: (_) => appState,
      child: const ReshaqaApp(),
    ),
  );
}

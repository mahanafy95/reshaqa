import 'package:flutter/material.dart';

/// ثيم رشاقة — ألوان هادئة وداعمة، عربي RTL.
class AppColors {
  static const teal = Color(0xFF1B998B);
  static const tealDark = Color(0xFF147a6e);
  static const orange = Color(0xFFE08A3C);
  static const blue = Color(0xFF3C7DD9);
  static const bg = Color(0xFFF6F8F7);
  static const card = Colors.white;
  static const textDark = Color(0xFF1F2933);
  static const textMuted = Color(0xFF6B7280);
  static const danger = Color(0xFFD9534F);
  static const success = Color(0xFF1B998B);
}

ThemeData buildTheme() {
  final base = ThemeData(
    useMaterial3: true,
    colorSchemeSeed: AppColors.teal,
    scaffoldBackgroundColor: AppColors.bg,
    fontFamily: 'Roboto',
  );
  return base.copyWith(
    appBarTheme: const AppBarTheme(
      backgroundColor: AppColors.teal,
      foregroundColor: Colors.white,
      elevation: 0,
      centerTitle: true,
    ),
    cardTheme: CardThemeData(
      color: AppColors.card,
      elevation: 1.5,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      margin: const EdgeInsets.symmetric(vertical: 6, horizontal: 0),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.teal,
        foregroundColor: Colors.white,
        minimumSize: const Size.fromHeight(52),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white,
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    ),
    snackBarTheme: const SnackBarThemeData(behavior: SnackBarBehavior.floating),
  );
}

/// ألوان الوضع الليلي (سطح وخلفية داكنة بلمسة خضراء، ونص فاتح مريح).
class DarkColors {
  static const bg = Color(0xFF0E1513);
  static const surface = Color(0xFF18211E);
  static const textMuted = Color(0xFF9AA4A1);
}

ThemeData buildDarkTheme() {
  final base = ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    colorSchemeSeed: AppColors.teal,
    scaffoldBackgroundColor: DarkColors.bg,
    fontFamily: 'Roboto',
  );
  return base.copyWith(
    colorScheme: base.colorScheme.copyWith(surface: DarkColors.surface),
    appBarTheme: const AppBarTheme(
      backgroundColor: AppColors.teal,
      foregroundColor: Colors.white,
      elevation: 0,
      centerTitle: true,
    ),
    cardTheme: CardThemeData(
      color: DarkColors.surface,
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      margin: const EdgeInsets.symmetric(vertical: 6, horizontal: 0),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.teal,
        foregroundColor: Colors.white,
        minimumSize: const Size.fromHeight(52),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: DarkColors.surface,
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    ),
    snackBarTheme: const SnackBarThemeData(behavior: SnackBarBehavior.floating),
  );
}

/// لون نصّ ثانوي يتكيّف مع الوضع (فاتح/داكن) — بديل آمن لـ AppColors.textMuted.
Color mutedColor(BuildContext context) =>
    Theme.of(context).brightness == Brightness.dark ? DarkColors.textMuted : AppColors.textMuted;

/// لون سطح البطاقة حسب الوضع — بديل لـ Colors.white / AppColors.card المثبّتة.
Color surfaceColor(BuildContext context) =>
    Theme.of(context).brightness == Brightness.dark ? DarkColors.surface : AppColors.card;

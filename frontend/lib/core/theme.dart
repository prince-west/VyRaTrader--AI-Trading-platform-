// lib/core/theme.dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class VyRaTheme {
  // ============================================================================
  // CORE COLORS (Blueprint Section 11 - Visual Identity)
  // ============================================================================

  /// Cyan blue neon primary theme (#00FFFF)
  static const Color cyan = Color(0xFF00FFFF);

  /// Dark gradient background start (#000C1F)
  static const Color bgTop = Color(0xFF000C1F);

  /// Dark gradient background end (#001F3F)
  static const Color bgBottom = Color(0xFF001F3F);

  /// Neon blue accent
  static const Color neonBlue = Color(0xFF00D9FF);

  /// Electric blue for highlights
  static const Color electricBlue = Color(0xFF0099FF);

  /// Success green (for profits, confirmations)
  static const Color successGreen = Color(0xFF00FF88);

  /// Error red (for losses, alerts)
  static const Color errorRed = Color(0xFFFF3366);

  /// Warning amber
  static const Color warningAmber = Color(0xFFFFAA00);

  /// Neutral gray
  static const Color neutralGray = Color(0xFF808080);

  /// Card background (semi-transparent)
  static const Color cardBg = Color(0xFF0A1929);

  /// Input field background
  static const Color inputBg = Color(0xFF071226);

  // ============================================================================
  // GRADIENTS
  // ============================================================================

  /// Main background gradient (dark blue)
  static const LinearGradient backgroundGradient = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [bgTop, bgBottom],
  );

  /// Cyan glow gradient (for buttons, cards)
  static const LinearGradient cyanGlowGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [cyan, electricBlue],
  );

  /// Success gradient (for profit displays)
  static const LinearGradient successGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [successGreen, Color(0xFF00CC66)],
  );

  /// Error gradient (for loss displays)
  static const LinearGradient errorGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [errorRed, Color(0xFFCC0044)],
  );

  // ============================================================================
  // SHADOWS & GLOWS
  // ============================================================================

  /// Cyan glow effect (for glowing elements)
  static List<BoxShadow> get cyanGlow => [
        BoxShadow(
            color: cyan.withOpacity(0.5), blurRadius: 20, spreadRadius: 2),
        BoxShadow(
            color: cyan.withOpacity(0.3), blurRadius: 40, spreadRadius: 5),
      ];

  /// Soft shadow (for cards)
  static List<BoxShadow> get softShadow => [
        BoxShadow(
          color: Colors.black.withOpacity(0.3),
          blurRadius: 10,
          offset: const Offset(0, 4),
        ),
      ];

  /// Electric glow (for active elements)
  static List<BoxShadow> get electricGlow => [
        BoxShadow(
          color: electricBlue.withOpacity(0.6),
          blurRadius: 15,
          spreadRadius: 1,
        ),
      ];

  // ============================================================================
  // DARK THEME (Main Theme)
  // ============================================================================

  static ThemeData get darkTheme {
    final base = ThemeData.dark();
    return base.copyWith(
      // Scaffold
      scaffoldBackgroundColor: Colors.black,

      // Primary color
      primaryColor: cyan,

      // Color scheme
      colorScheme: ColorScheme.dark(
        primary: cyan,
        secondary: neonBlue,
        tertiary: electricBlue,
        error: errorRed,
        surface: cardBg,
        onPrimary: Colors.black,
        onSecondary: Colors.black,
        onError: Colors.white,
        onSurface: Colors.white,
      ),

      // AppBar
      appBarTheme: AppBarTheme(
        backgroundColor: Colors.transparent,
        elevation: 0,
        centerTitle: true,
        iconTheme: const IconThemeData(color: cyan, size: 24),
        titleTextStyle: const TextStyle(
          color: cyan,
          fontSize: 16,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.5,
        ),
        systemOverlayStyle: SystemUiOverlayStyle.light,
      ),

      // Text theme
      textTheme: base.textTheme
          .apply(
            bodyColor: Colors.white,
            displayColor: Colors.white,
            fontFamily: 'Roboto',
          )
          .copyWith(
            displayLarge: const TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.w700,
              color: cyan,
              letterSpacing: 0.5,
            ),
            displayMedium: const TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w600,
              color: Colors.white,
            ),
            displaySmall: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w600,
              color: Colors.white,
            ),
            headlineLarge: const TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w600,
              color: cyan,
            ),
            headlineMedium: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w600,
              color: Colors.white,
            ),
            bodyLarge: const TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w400,
              color: Colors.white,
            ),
            bodyMedium: const TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w400,
              color: Colors.white70,
            ),
            bodySmall: const TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w400,
              color: Colors.white60,
            ),
            labelLarge: const TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: cyan,
              letterSpacing: 0.5,
            ),
          ),

      // Card theme
      cardTheme: CardThemeData(
        color: cardBg,
        elevation: 4,
        shadowColor: Colors.black.withOpacity(0.5),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(color: cyan.withOpacity(0.2), width: 1),
        ),
      ),

      // Elevated button
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: cyan,
          foregroundColor: Colors.black,
          elevation: 4,
          shadowColor: cyan.withOpacity(0.5),
          padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          textStyle: const TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.5,
          ),
        ),
      ),

      // Outlined button
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: cyan,
          side: const BorderSide(color: cyan, width: 2),
          padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          textStyle: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.5,
          ),
        ),
      ),

      // Text button
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: cyan,
          textStyle: const TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.5,
          ),
        ),
      ),

      // Input decoration
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: inputBg,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 16,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: cyan.withOpacity(0.3)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: cyan.withOpacity(0.3)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: cyan, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: errorRed, width: 2),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: errorRed, width: 2),
        ),
        labelStyle: const TextStyle(color: Colors.white70),
        hintStyle: const TextStyle(color: Colors.white38),
        errorStyle: const TextStyle(color: errorRed),
        prefixIconColor: cyan,
        suffixIconColor: cyan,
      ),

      // Icon theme
      iconTheme: const IconThemeData(color: cyan, size: 24),

      // Floating action button
      floatingActionButtonTheme: FloatingActionButtonThemeData(
        backgroundColor: cyan,
        foregroundColor: Colors.black,
        elevation: 8,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      ),

      // Bottom navigation bar
      bottomNavigationBarTheme: BottomNavigationBarThemeData(
        backgroundColor: cardBg,
        selectedItemColor: cyan,
        unselectedItemColor: Colors.white38,
        elevation: 8,
        type: BottomNavigationBarType.fixed,
        selectedLabelStyle: const TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w600,
        ),
        unselectedLabelStyle: const TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w400,
        ),
      ),

      // Divider
      dividerTheme: DividerThemeData(
        color: cyan.withOpacity(0.2),
        thickness: 1,
        space: 16,
      ),

      // Slider
      sliderTheme: SliderThemeData(
        activeTrackColor: cyan,
        inactiveTrackColor: cyan.withOpacity(0.3),
        thumbColor: cyan,
        overlayColor: cyan.withOpacity(0.2),
        valueIndicatorColor: cyan,
        valueIndicatorTextStyle: const TextStyle(
          color: Colors.black,
          fontWeight: FontWeight.w600,
        ),
      ),

      // Switch
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return cyan;
          }
          return Colors.white38;
        }),
        trackColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return cyan.withOpacity(0.5);
          }
          return Colors.white12;
        }),
      ),

      // Checkbox
      checkboxTheme: CheckboxThemeData(
        fillColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return cyan;
          }
          return Colors.transparent;
        }),
        checkColor: WidgetStateProperty.all(Colors.black),
        side: const BorderSide(color: cyan, width: 2),
      ),

      // Radio
      radioTheme: RadioThemeData(
        fillColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return cyan;
          }
          return Colors.white38;
        }),
      ),

      // Dialog
      dialogTheme: DialogThemeData(
        backgroundColor: cardBg,
        elevation: 8,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(color: cyan.withOpacity(0.3)),
        ),
        titleTextStyle: const TextStyle(
          color: cyan,
          fontSize: 20,
          fontWeight: FontWeight.w700,
        ),
        contentTextStyle: const TextStyle(color: Colors.white, fontSize: 14),
      ),

      // Snackbar
      snackBarTheme: SnackBarThemeData(
        backgroundColor: cardBg,
        contentTextStyle: const TextStyle(color: Colors.white, fontSize: 14),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(color: cyan.withOpacity(0.3)),
        ),
        behavior: SnackBarBehavior.floating,
      ),

      // Progress indicator
      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: cyan,
        circularTrackColor: Colors.white12,
        linearTrackColor: Colors.white12,
      ),
    );
  }

  // ============================================================================
  // LIGHT THEME (Optional - for future use)
  // ============================================================================

  static ThemeData get lightTheme {
    final base = ThemeData.light();
    return base.copyWith(
      scaffoldBackgroundColor: Colors.white,
      primaryColor: const Color(0xFF0099CC),
      colorScheme: ColorScheme.light(
        primary: const Color(0xFF0099CC),
        secondary: const Color(0xFF00BBFF),
        error: errorRed,
        surface: Colors.white,
      ),
      // Add more light theme customization if needed
    );
  }

  // ============================================================================
  // HELPER METHODS
  // ============================================================================

  /// Get gradient box decoration (for containers)
  static BoxDecoration getGradientDecoration({
    Gradient? gradient,
    double borderRadius = 16,
    List<BoxShadow>? shadows,
    Border? border,
  }) {
    return BoxDecoration(
      gradient: gradient ?? backgroundGradient,
      borderRadius: BorderRadius.circular(borderRadius),
      boxShadow: shadows,
      border: border,
    );
  }

  /// Get glowing card decoration
  static BoxDecoration getGlowingCard({
    double borderRadius = 16,
    Color? glowColor,
  }) {
    return BoxDecoration(
      color: cardBg,
      borderRadius: BorderRadius.circular(borderRadius),
      border: Border.all(color: (glowColor ?? cyan).withOpacity(0.3), width: 1),
      boxShadow: [
        BoxShadow(
          color: (glowColor ?? cyan).withOpacity(0.2),
          blurRadius: 15,
          spreadRadius: 1,
        ),
      ],
    );
  }
}

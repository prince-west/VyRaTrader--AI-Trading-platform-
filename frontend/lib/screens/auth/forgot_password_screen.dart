// lib/screens/auth/forgot_password_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'dart:ui';
import '../../core/api_client.dart';
import '../../core/theme.dart';
import '../../core/constants.dart';
import '../../widgets/glow_button.dart';

class ForgotPasswordScreen extends StatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  State<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen>
    with SingleTickerProviderStateMixin {
  final _emailController = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  bool _loading = false;
  String? _message;
  bool _isSuccess = false;
  late AnimationController _glowController;

  @override
  void initState() {
    super.initState();
    _glowController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _emailController.dispose();
    _glowController.dispose();
    super.dispose();
  }

  Future<void> _reset() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _loading = true;
      _message = null;
    });

    try {
      final api = Provider.of<ApiClient>(context, listen: false);
      final res = await api.post('/api/v1/auth/forgot-password', {
        'email': _emailController.text.trim(),
      });

      setState(() {
        _isSuccess = true;
        _message = res['message'] ??
            'Password reset instructions have been sent to your email.';
      });

      // Auto-navigate back after 3 seconds
      Future.delayed(const Duration(seconds: 3), () {
        if (mounted) {
          Navigator.pop(context);
        }
      });
    } catch (e) {
      setState(() {
        _isSuccess = false;
        _message =
            'Failed to send reset link. Please check your email and try again.';
      });
    } finally {
      setState(() => _loading = false);
    }
  }

  String? _validateEmail(String? value) {
    if (value == null || value.isEmpty) {
      return 'Email is required';
    }
    if (!RegExp(EmailRules.pattern).hasMatch(value)) {
      return 'Please enter a valid email address';
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;

    return Scaffold(
      body: Container(
        width: double.infinity,
        height: double.infinity,
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [VyRaTheme.bgTop, VyRaTheme.bgBottom],
          ),
        ),
        child: Stack(
          children: [
            // Animated background particles
            ...List.generate(30, (index) {
              return Positioned(
                left: (index * 37.0) % size.width,
                top: (index * 53.0) % size.height,
                child: AnimatedBuilder(
                  animation: _glowController,
                  builder: (context, child) {
                    final delay = index * 0.05;
                    final value = (_glowController.value + delay) % 1.0;
                    return Opacity(
                      opacity: 0.1 + value * 0.3,
                      child: Container(
                        width: 4 + (index % 3) * 2,
                        height: 4 + (index % 3) * 2,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: VyRaTheme.cyan,
                          boxShadow: [
                            BoxShadow(
                              color: VyRaTheme.cyan.withOpacity(0.5),
                              blurRadius: 10,
                              spreadRadius: 2,
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              );
            }),

            // Main content
            SafeArea(
              child: Column(
                children: [
                  // Back button
                  Padding(
                    padding: const EdgeInsets.all(16),
                    child: Align(
                      alignment: Alignment.centerLeft,
                      child: IconButton(
                        onPressed: () => Navigator.pop(context),
                        icon: Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: VyRaTheme.cardBg,
                            shape: BoxShape.circle,
                            border: Border.all(
                              color: VyRaTheme.cyan.withOpacity(0.3),
                              width: 1,
                            ),
                            boxShadow: VyRaTheme.softShadow,
                          ),
                          child: const Icon(
                            Icons.arrow_back,
                            color: VyRaTheme.cyan,
                            size: 24,
                          ),
                        ),
                      ),
                    ),
                  ),

                  // Scrollable content
                  Expanded(
                    child: Center(
                      child: SingleChildScrollView(
                        padding: const EdgeInsets.symmetric(horizontal: 24),
                        child: Form(
                          key: _formKey,
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              // Glowing icon
                              AnimatedBuilder(
                                animation: _glowController,
                                builder: (context, child) {
                                  return Container(
                                    padding: const EdgeInsets.all(24),
                                    decoration: BoxDecoration(
                                      shape: BoxShape.circle,
                                      gradient: LinearGradient(
                                        colors: [
                                          VyRaTheme.cyan.withOpacity(
                                            0.2 + _glowController.value * 0.3,
                                          ),
                                          VyRaTheme.electricBlue.withOpacity(
                                            0.2 + _glowController.value * 0.3,
                                          ),
                                        ],
                                      ),
                                      boxShadow: [
                                        BoxShadow(
                                          color: VyRaTheme.cyan.withOpacity(
                                            0.3 + _glowController.value * 0.2,
                                          ),
                                          blurRadius: 40,
                                          spreadRadius: 10,
                                        ),
                                      ],
                                    ),
                                    child: Icon(
                                      _isSuccess
                                          ? Icons.check_circle_outline
                                          : Icons.lock_reset,
                                      size: 64,
                                      color: VyRaTheme.cyan,
                                    ),
                                  );
                                },
                              ),

                              const SizedBox(height: 32),

                              // Title
                              ShaderMask(
                                shaderCallback: (bounds) {
                                  return const LinearGradient(
                                    colors: [
                                      VyRaTheme.cyan,
                                      VyRaTheme.electricBlue,
                                    ],
                                  ).createShader(bounds);
                                },
                                child: const Text(
                                  'Forgot Password?',
                                  style: TextStyle(
                                    fontSize: 32,
                                    fontWeight: FontWeight.bold,
                                    color: Colors.white,
                                  ),
                                  textAlign: TextAlign.center,
                                ),
                              ),

                              const SizedBox(height: 16),

                              // Subtitle
                              Text(
                                _isSuccess
                                    ? 'Check your email for the reset link'
                                    : 'Enter your email and we\'ll send you\ninstructions to reset your password',
                                style: TextStyle(
                                  fontSize: 14,
                                  color: Colors.white.withOpacity(0.7),
                                  height: 1.5,
                                ),
                                textAlign: TextAlign.center,
                              ),

                              const SizedBox(height: 48),

                              // Email input
                              if (!_isSuccess) ...[
                                Container(
                                  decoration: BoxDecoration(
                                    borderRadius: BorderRadius.circular(16),
                                    boxShadow: [
                                      BoxShadow(
                                        color: VyRaTheme.cyan.withOpacity(0.1),
                                        blurRadius: 20,
                                        spreadRadius: 2,
                                      ),
                                    ],
                                  ),
                                  child: TextFormField(
                                    controller: _emailController,
                                    enabled: !_loading,
                                    keyboardType: TextInputType.emailAddress,
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontSize: 16,
                                    ),
                                    validator: _validateEmail,
                                    decoration: InputDecoration(
                                      labelText: 'Email Address',
                                      labelStyle: TextStyle(
                                        color: VyRaTheme.cyan.withOpacity(0.7),
                                      ),
                                      hintText: 'you@example.com',
                                      hintStyle: TextStyle(
                                        color: Colors.white.withOpacity(0.3),
                                      ),
                                      prefixIcon: const Icon(
                                        Icons.email_outlined,
                                        color: VyRaTheme.cyan,
                                      ),
                                      filled: true,
                                      fillColor: VyRaTheme.inputBg,
                                      border: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(16),
                                        borderSide: BorderSide(
                                          color: VyRaTheme.cyan.withOpacity(
                                            0.3,
                                          ),
                                        ),
                                      ),
                                      enabledBorder: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(16),
                                        borderSide: BorderSide(
                                          color: VyRaTheme.cyan.withOpacity(
                                            0.3,
                                          ),
                                          width: 1,
                                        ),
                                      ),
                                      focusedBorder: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(16),
                                        borderSide: const BorderSide(
                                          color: VyRaTheme.cyan,
                                          width: 2,
                                        ),
                                      ),
                                      errorBorder: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(16),
                                        borderSide: const BorderSide(
                                          color: VyRaTheme.errorRed,
                                          width: 1,
                                        ),
                                      ),
                                      focusedErrorBorder: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(16),
                                        borderSide: const BorderSide(
                                          color: VyRaTheme.errorRed,
                                          width: 2,
                                        ),
                                      ),
                                      contentPadding:
                                          const EdgeInsets.symmetric(
                                        horizontal: 20,
                                        vertical: 20,
                                      ),
                                    ),
                                  ),
                                ),

                                const SizedBox(height: 32),

                                // Submit button
                                SizedBox(
                                  width: double.infinity,
                                  height: 56,
                                  child: GlowButton(
                                    text: _loading
                                        ? 'Sending...'
                                        : 'Send Reset Link',
                                    glowColor: VyRaTheme.cyan,
                                    onPressed: _loading ? null : _reset,
                                  ),
                                ),
                              ],

                              // Message display
                              if (_message != null) ...[
                                const SizedBox(height: 24),
                                Container(
                                  padding: const EdgeInsets.all(16),
                                  decoration: BoxDecoration(
                                    color: _isSuccess
                                        ? VyRaTheme.successGreen.withOpacity(
                                            0.1,
                                          )
                                        : VyRaTheme.errorRed.withOpacity(0.1),
                                    borderRadius: BorderRadius.circular(12),
                                    border: Border.all(
                                      color: _isSuccess
                                          ? VyRaTheme.successGreen.withOpacity(
                                              0.3,
                                            )
                                          : VyRaTheme.errorRed.withOpacity(0.3),
                                      width: 1,
                                    ),
                                  ),
                                  child: Row(
                                    children: [
                                      Icon(
                                        _isSuccess
                                            ? Icons.check_circle
                                            : Icons.error_outline,
                                        color: _isSuccess
                                            ? VyRaTheme.successGreen
                                            : VyRaTheme.errorRed,
                                        size: 24,
                                      ),
                                      const SizedBox(width: 12),
                                      Expanded(
                                        child: Text(
                                          _message!,
                                          style: TextStyle(
                                            color: _isSuccess
                                                ? VyRaTheme.successGreen
                                                : VyRaTheme.errorRed,
                                            fontSize: 14,
                                            height: 1.5,
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ],

                              const SizedBox(height: 32),

                              // Back to login
                              TextButton(
                                onPressed: () => Navigator.pop(context),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    const Icon(
                                      Icons.arrow_back,
                                      color: VyRaTheme.cyan,
                                      size: 18,
                                    ),
                                    const SizedBox(width: 8),
                                    Text(
                                      'Back to Login',
                                      style: TextStyle(
                                        color: VyRaTheme.cyan,
                                        fontSize: 14,
                                        fontWeight: FontWeight.w600,
                                        decoration: TextDecoration.underline,
                                        decorationColor:
                                            VyRaTheme.cyan.withOpacity(0.5),
                                      ),
                                    ),
                                  ],
                                ),
                              ),

                              const SizedBox(height: 48),

                              // Support info
                              Container(
                                padding: const EdgeInsets.all(16),
                                decoration: BoxDecoration(
                                  color: VyRaTheme.cardBg.withOpacity(0.5),
                                  borderRadius: BorderRadius.circular(12),
                                  border: Border.all(
                                    color: VyRaTheme.cyan.withOpacity(0.2),
                                    width: 1,
                                  ),
                                ),
                                child: Column(
                                  children: [
                                    Icon(
                                      Icons.help_outline,
                                      color: VyRaTheme.cyan.withOpacity(0.7),
                                      size: 24,
                                    ),
                                    const SizedBox(height: 8),
                                    Text(
                                      'Need Help?',
                                      style: TextStyle(
                                        color: Colors.white.withOpacity(0.9),
                                        fontSize: 14,
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      'Contact support at support@vyratrader.com',
                                      style: TextStyle(
                                        color: Colors.white.withOpacity(0.6),
                                        fontSize: 12,
                                      ),
                                      textAlign: TextAlign.center,
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),

            // Loading overlay
            if (_loading)
              Positioned.fill(
                child: Container(
                  color: Colors.black.withOpacity(0.7),
                  child: BackdropFilter(
                    filter: ImageFilter.blur(sigmaX: 5, sigmaY: 5),
                    child: Center(
                      child: Container(
                        padding: const EdgeInsets.all(24),
                        decoration: BoxDecoration(
                          color: VyRaTheme.cardBg,
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(
                            color: VyRaTheme.cyan.withOpacity(0.3),
                            width: 1,
                          ),
                          boxShadow: VyRaTheme.cyanGlow,
                        ),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const SizedBox(
                              width: 40,
                              height: 40,
                              child: CircularProgressIndicator(
                                valueColor: AlwaysStoppedAnimation<Color>(
                                  VyRaTheme.cyan,
                                ),
                                strokeWidth: 3,
                              ),
                            ),
                            const SizedBox(height: 16),
                            const Text(
                              'Sending reset link...',
                              style: TextStyle(
                                color: VyRaTheme.cyan,
                                fontSize: 14,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

// Note: Currencies are not relevant for password reset screen
// They are used in trading/payment screens and are available via constants.dart

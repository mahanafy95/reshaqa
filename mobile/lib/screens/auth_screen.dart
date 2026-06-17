import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/theme.dart';
import '../state/app_state.dart';

/// شاشة الدخول/التسجيل بـ username وكلمة سر (بدون إيميل).
class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});
  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  final _user = TextEditingController();
  final _pass = TextEditingController();
  bool _isLogin = true;
  bool _busy = false;
  String? _error;

  Future<void> _submit() async {
    final u = _user.text.trim();
    final p = _pass.text;
    if (u.length < 3 || p.length < 6) {
      setState(() => _error = 'اسم المستخدم 3 أحرف على الأقل وكلمة السر 6 على الأقل.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final app = context.read<AppState>();
      if (_isLogin) {
        await app.login(u, p);
      } else {
        await app.register(u, p);
      }
    } catch (e) {
      setState(() => _error = ApiClient.errorMessage(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              children: [
                const SizedBox(height: 20),
                const Icon(Icons.eco_rounded, size: 72, color: AppColors.teal),
                const SizedBox(height: 12),
                const Text('رشاقة', style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: AppColors.teal)),
                const SizedBox(height: 4),
                const Text('رحلتك للتخسيس الصحي تبدأ من هنا 💚', style: TextStyle(color: AppColors.textMuted)),
                const SizedBox(height: 32),
                TextField(
                  controller: _user,
                  textInputAction: TextInputAction.next,
                  decoration: const InputDecoration(labelText: 'اسم المستخدم', prefixIcon: Icon(Icons.person_outline)),
                ),
                const SizedBox(height: 14),
                TextField(
                  controller: _pass,
                  obscureText: true,
                  decoration: const InputDecoration(labelText: 'كلمة السر', prefixIcon: Icon(Icons.lock_outline)),
                ),
                if (_error != null) ...[
                  const SizedBox(height: 12),
                  Text(_error!, style: const TextStyle(color: AppColors.danger), textAlign: TextAlign.center),
                ],
                const SizedBox(height: 22),
                ElevatedButton(
                  onPressed: _busy ? null : _submit,
                  child: _busy
                      ? const SizedBox(height: 22, width: 22, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                      : Text(_isLogin ? 'دخول' : 'إنشاء حساب'),
                ),
                const SizedBox(height: 12),
                TextButton(
                  onPressed: _busy ? null : () => setState(() => _isLogin = !_isLogin),
                  child: Text(_isLogin ? 'معندكش حساب؟ سجّل دلوقتي' : 'عندك حساب؟ سجّل دخول'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

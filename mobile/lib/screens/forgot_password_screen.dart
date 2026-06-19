import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/theme.dart';
import '../services/api.dart';
import '../state/app_state.dart';

/// شاشة استرجاع كلمة السر بالبريد (رمز OTP مجاني — بدون SMS).
class ForgotPasswordScreen extends StatefulWidget {
  const ForgotPasswordScreen({super.key});
  @override
  State<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
  final _email = TextEditingController();
  final _code = TextEditingController();
  final _newPass = TextEditingController();
  int _step = 1;
  bool _busy = false;
  String? _error;
  String? _info;

  Future<void> _requestCode() async {
    final e = _email.text.trim();
    if (e.isEmpty) {
      setState(() => _error = 'اكتب بريدك الإلكتروني.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final r = await Api.forgotPassword(e);
      setState(() {
        _info = (r['message'] ?? 'لو البريد مسجّل، هيوصلك رمز.').toString();
        _step = 2;
      });
    } catch (err) {
      setState(() => _error = ApiClient.errorMessage(err));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _reset() async {
    final code = _code.text.trim();
    final np = _newPass.text;
    if (code.length < 4 || np.length < 6) {
      setState(() => _error = 'اكتب الرمز وكلمة سر جديدة (6 أحرف على الأقل).');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await Api.resetPassword(_email.text.trim(), code, np);
      if (!mounted) return;
      // أعِد تهيئة الحالة بالتوكن الجديد ثم ارجع
      await context.read<AppState>().bootstrap();
      if (mounted) Navigator.of(context).pop();
    } catch (err) {
      setState(() => _error = ApiClient.errorMessage(err));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('استرجاع كلمة السر')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 8),
              const Icon(Icons.lock_reset, size: 64, color: AppColors.teal),
              const SizedBox(height: 12),
              Text(
                _step == 1 ? 'هنبعتلك رمز على إيميلك' : 'اكتب الرمز اللي وصلك وكلمة سر جديدة',
                textAlign: TextAlign.center,
                style: TextStyle(color: mutedColor(context)),
              ),
              const SizedBox(height: 24),
              if (_step == 1) ...[
                TextField(
                  controller: _email,
                  keyboardType: TextInputType.emailAddress,
                  decoration: const InputDecoration(
                    labelText: 'البريد الإلكتروني',
                    prefixIcon: Icon(Icons.email_outlined),
                  ),
                ),
              ] else ...[
                if (_info != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: Text(_info!,
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: AppColors.teal)),
                  ),
                TextField(
                  controller: _code,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                    labelText: 'الرمز (6 أرقام)',
                    prefixIcon: Icon(Icons.pin_outlined),
                  ),
                ),
                const SizedBox(height: 14),
                TextField(
                  controller: _newPass,
                  obscureText: true,
                  decoration: const InputDecoration(
                    labelText: 'كلمة السر الجديدة',
                    prefixIcon: Icon(Icons.lock_outline),
                  ),
                ),
              ],
              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(_error!,
                    style: const TextStyle(color: AppColors.danger),
                    textAlign: TextAlign.center),
              ],
              const SizedBox(height: 22),
              ElevatedButton(
                onPressed: _busy ? null : (_step == 1 ? _requestCode : _reset),
                child: _busy
                    ? const SizedBox(
                        height: 22,
                        width: 22,
                        child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                    : Text(_step == 1 ? 'ابعت الرمز' : 'غيّر كلمة السر وادخل'),
              ),
              if (_step == 2)
                TextButton(
                  onPressed: _busy
                      ? null
                      : () => setState(() {
                            _step = 1;
                            _error = null;
                            _info = null;
                          }),
                  child: const Text('مطلعش الرمز؟ ابعت تاني'),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

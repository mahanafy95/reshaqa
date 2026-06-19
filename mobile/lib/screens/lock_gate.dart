import 'package:flutter/material.dart';

import '../core/theme.dart';
import '../services/biometric_service.dart';

/// بوابة قفل بيومتري/PIN — تظهر قبل المحتوى لو القفل مفعّل.
class LockGate extends StatefulWidget {
  const LockGate({super.key, required this.child});
  final Widget child;

  @override
  State<LockGate> createState() => _LockGateState();
}

class _LockGateState extends State<LockGate> with WidgetsBindingObserver {
  bool _checking = true;
  bool _unlocked = false;
  bool _lockEnabled = false;
  bool _authInProgress = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _maybeLock();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (!_lockEnabled) return;
    if (state == AppLifecycleState.paused || state == AppLifecycleState.inactive) {
      // لمّا التطبيق يروح للخلفية، نقفل تاني ونطلب التحقق عند الرجوع.
      if (!_authInProgress && _unlocked) {
        setState(() => _unlocked = false);
      }
    } else if (state == AppLifecycleState.resumed) {
      if (!_unlocked) _tryUnlock();
    }
  }

  Future<void> _maybeLock() async {
    final enabled = await BiometricService.isLockEnabled();
    _lockEnabled = enabled;
    if (!enabled) {
      setState(() {
        _unlocked = true;
        _checking = false;
      });
      return;
    }
    setState(() => _checking = false);
    _tryUnlock();
  }

  Future<void> _tryUnlock() async {
    if (_authInProgress) return; // نتجنّب طلب التحقق مرتين في نفس الوقت
    _authInProgress = true;
    try {
      final ok = await BiometricService.authenticate();
      if (mounted) setState(() => _unlocked = ok);
    } finally {
      _authInProgress = false;
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_checking) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (_unlocked) return widget.child;
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.lock_rounded, size: 72, color: AppColors.teal),
            const SizedBox(height: 16),
            const Text('رشاقة مقفولة', style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Text('افتح ببصمتك أو رقمك السري', style: TextStyle(color: mutedColor(context))),
            const SizedBox(height: 24),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 40),
              child: ElevatedButton.icon(
                onPressed: _tryUnlock,
                icon: const Icon(Icons.fingerprint),
                label: const Text('فتح'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

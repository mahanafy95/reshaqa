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

class _LockGateState extends State<LockGate> {
  bool _checking = true;
  bool _unlocked = false;

  @override
  void initState() {
    super.initState();
    _maybeLock();
  }

  Future<void> _maybeLock() async {
    final enabled = await BiometricService.isLockEnabled();
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
    final ok = await BiometricService.authenticate();
    if (mounted) setState(() => _unlocked = ok);
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
            const Text('افتح ببصمتك أو رقمك السري', style: TextStyle(color: AppColors.textMuted)),
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

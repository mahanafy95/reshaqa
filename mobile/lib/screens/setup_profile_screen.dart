import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/theme.dart';
import '../state/app_state.dart';

/// إعداد الملف الشخصي — أساس حساب الأهداف (مع منع الوزن غير الصحي من الخادم).
class SetupProfileScreen extends StatefulWidget {
  const SetupProfileScreen({super.key});
  @override
  State<SetupProfileScreen> createState() => _SetupProfileScreenState();
}

class _SetupProfileScreenState extends State<SetupProfileScreen> {
  final _age = TextEditingController();
  final _height = TextEditingController();
  final _weight = TextEditingController();
  final _goalWeight = TextEditingController();
  String _sex = 'female';
  String _activity = 'light';
  double _rate = 0.5;
  bool _busy = false;
  String? _error;

  static const _activityLabels = {
    'sedentary': 'خامل (مكتبي/قليل الحركة)',
    'light': 'نشاط خفيف (مشي بسيط)',
    'moderate': 'نشاط متوسط (تمرين 3-5 أيام)',
    'active': 'نشاط عالٍ (تمرين يومي)',
  };

  Future<void> _save() async {
    final age = int.tryParse(_age.text);
    final height = double.tryParse(_height.text);
    final weight = double.tryParse(_weight.text);
    final goal = double.tryParse(_goalWeight.text);
    if (age == null || height == null || weight == null) {
      setState(() => _error = 'املأ العمر والطول والوزن صح.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await context.read<AppState>().saveProfile({
        'age': age,
        'sex': _sex,
        'height_cm': height,
        'weight_kg': weight,
        'activity_level': _activity,
        'goal_weight_kg': goal,
        'goal_rate': _rate,
      });
    } catch (e) {
      setState(() => _error = ApiClient.errorMessage(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('بياناتك')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('عشان نحسبلك هدف صحي وآمن، محتاجين شوية بيانات 🙂',
                style: TextStyle(color: AppColors.textMuted)),
            const SizedBox(height: 16),
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'female', label: Text('أنثى')),
                ButtonSegment(value: 'male', label: Text('ذكر')),
              ],
              selected: {_sex},
              onSelectionChanged: (s) => setState(() => _sex = s.first),
            ),
            const SizedBox(height: 14),
            _num(_age, 'العمر (سنة)'),
            _num(_height, 'الطول (سم)'),
            _num(_weight, 'الوزن الحالي (كجم)'),
            _num(_goalWeight, 'الوزن المستهدف (كجم) — اختياري'),
            const SizedBox(height: 8),
            const Align(alignment: Alignment.centerRight, child: Text('مستوى النشاط')),
            const SizedBox(height: 6),
            DropdownButtonFormField<String>(
              initialValue: _activity,
              items: _activityLabels.entries
                  .map((e) => DropdownMenuItem(value: e.key, child: Text(e.value)))
                  .toList(),
              onChanged: (v) => setState(() => _activity = v!),
            ),
            const SizedBox(height: 16),
            Text('معدل النزول المطلوب: ${_rate.toStringAsFixed(2)} كجم/أسبوع'),
            Slider(
              value: _rate,
              min: 0.25,
              max: 0.75,
              divisions: 2,
              label: '${_rate.toStringAsFixed(2)} كجم',
              onChanged: (v) => setState(() => _rate = v),
            ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Text(_error!, style: const TextStyle(color: AppColors.danger)),
              ),
            const SizedBox(height: 8),
            ElevatedButton(
              onPressed: _busy ? null : _save,
              child: _busy
                  ? const SizedBox(height: 22, width: 22, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                  : const Text('احسبلي هدفي'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _num(TextEditingController c, String label) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: TextField(
          controller: c,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: InputDecoration(labelText: label),
        ),
      );
}

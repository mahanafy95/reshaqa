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
  final _allergies = TextEditingController();
  String _sex = 'female';
  String _activity = 'light';
  String _diet = 'none';
  double _rate = 0.5;
  bool _busy = false;
  String? _error;

  static const _activityLabels = {
    'sedentary': 'خامل (مكتبي/قليل الحركة)',
    'light': 'نشاط خفيف (مشي بسيط)',
    'moderate': 'نشاط متوسط (تمرين 3-5 أيام)',
    'active': 'نشاط عالٍ (تمرين يومي)',
  };

  static const _dietLabels = {
    'none': 'بدون قيود',
    'halal': 'حلال فقط',
    'vegetarian': 'نباتي',
    'vegan': 'نباتي صِرف (فيجان)',
    'keto': 'كيتو',
    'low_carb': 'قليل الكارب',
  };

  /// تصنيف فوري حسب الطول والوزن المُدخَلين (نفس منطق الخادم).
  /// يُرجع (الحالة, BMI, الوزن المقترح) أو null لو البيانات ناقصة.
  ({String status, double bmi, double? recommended})? _classify() {
    final h = (double.tryParse(_height.text) ?? 0) / 100;
    final w = double.tryParse(_weight.text) ?? 0;
    if (h <= 0 || w <= 0) return null;
    final b = w / (h * h);
    final status = b < 18.5 ? 'underweight' : (b >= 25 ? 'overweight' : 'normal');
    double? rec;
    if (status == 'underweight') rec = (20 * h * h * 10).roundToDouble() / 10;
    if (status == 'overweight') rec = (24 * h * h * 10).roundToDouble() / 10;
    return (status: status, bmi: (b * 10).roundToDouble() / 10, recommended: rec);
  }

  static const _statusInfo = {
    'underweight': ('تحت الوزن الصحي', 'زيادة وزن', '⬆️', AppColors.blue),
    'normal': ('ضمن الوزن الصحي', 'تثبيت', '✅', AppColors.teal),
    'overweight': ('فوق الوزن الصحي', 'تخسيس', '⬇️', AppColors.orange),
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
        'dietary_pref': _diet,
        'allergies': _allergies.text.trim().isEmpty ? null : _allergies.text.trim(),
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
            _num(_height, 'الطول (سم)', live: true),
            _num(_weight, 'الوزن الحالي (كجم)', live: true),
            _num(_goalWeight, 'الوزن المستهدف (كجم) — اختياري'),
            _buildClassificationCard(),
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
            const Align(alignment: Alignment.centerRight, child: Text('النظام الغذائي (المساعد هيحترمه)')),
            const SizedBox(height: 6),
            DropdownButtonFormField<String>(
              initialValue: _diet,
              items: _dietLabels.entries
                  .map((e) => DropdownMenuItem(value: e.key, child: Text(e.value)))
                  .toList(),
              onChanged: (v) => setState(() => _diet = v!),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _allergies,
              decoration: const InputDecoration(
                labelText: 'حساسية / أكل تتجنّبه (اختياري)',
                hintText: 'مثال: مكسرات، لاكتوز',
              ),
            ),
            const SizedBox(height: 16),
            Builder(builder: (_) {
              final isGain = _classify()?.status == 'underweight';
              final rateMax = isGain ? 0.5 : 0.75;          // الزيادة الصحية أقصاها 0.5/أسبوع
              final divisions = isGain ? 1 : 2;
              final shown = _rate.clamp(0.25, rateMax);
              final word = isGain ? 'الزيادة' : 'النزول';
              return Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text('معدل $word المطلوب: ${shown.toStringAsFixed(2)} كجم/أسبوع'),
                  Slider(
                    value: shown,
                    min: 0.25,
                    max: rateMax,
                    divisions: divisions,
                    label: '${shown.toStringAsFixed(2)} كجم',
                    onChanged: (v) => setState(() => _rate = v),
                  ),
                ],
              );
            }),
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

  Widget _buildClassificationCard() {
    final c = _classify();
    if (c == null) return const SizedBox.shrink();
    final info = _statusInfo[c.status]!;
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: info.$4.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Text(info.$3, style: const TextStyle(fontSize: 26)),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('${info.$1} (BMI ${c.bmi})',
                        style: TextStyle(fontWeight: FontWeight.bold, color: info.$4)),
                    Text('البرنامج المناسب: ${info.$2}',
                        style: const TextStyle(color: AppColors.textMuted, fontSize: 13)),
                  ],
                ),
              ),
            ],
          ),
          if (c.recommended != null) ...[
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(child: Text('وزن مقترح صحي: ${c.recommended} كجم')),
                TextButton(
                  onPressed: () => setState(() => _goalWeight.text = '${c.recommended}'),
                  child: const Text('استخدمه كهدف'),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _num(TextEditingController c, String label, {bool live = false}) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: TextField(
          controller: c,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: InputDecoration(labelText: label),
          onChanged: live ? (_) => setState(() {}) : null,
        ),
      );
}

import 'package:flutter/material.dart';

import '../core/api_client.dart';
import '../core/theme.dart';
import '../services/api.dart';
import '../widgets/common.dart';

class MoodScreen extends StatefulWidget {
  const MoodScreen({super.key});
  @override
  State<MoodScreen> createState() => _MoodScreenState();
}

class _MoodScreenState extends State<MoodScreen> {
  double _energy = 3;
  double _hunger = 3;
  double _sleep = 7;
  bool _loading = true;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final m = await Api.mood();
      if (m != null) {
        _energy = (m['energy'] as num?)?.toDouble() ?? 3;
        _hunger = (m['hunger'] as num?)?.toDouble() ?? 3;
        _sleep = (m['sleep_hours'] as num?)?.toDouble() ?? 7;
      }
    } catch (_) {} finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _save() async {
    setState(() => _busy = true);
    try {
      await Api.saveMood({
        'energy': _energy.round(),
        'hunger': _hunger.round(),
        'sleep_hours': _sleep,
      });
      if (mounted) {
        showSnack(context, 'اتسجّل، شكراً إنك بتتابع حالتك 💚');
        Navigator.pop(context);
      }
    } catch (e) {
      if (mounted) showSnack(context, ApiClient.errorMessage(e), error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('حاسس بإيه النهاردة؟')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                _slider('طاقتك', _energy, 1, 5, '${_energy.round()}/5', (v) => setState(() => _energy = v), Icons.bolt, AppColors.orange),
                _slider('ساعات نومك', _sleep, 0, 12, '${_sleep.toStringAsFixed(1)} ساعة', (v) => setState(() => _sleep = v), Icons.bedtime, AppColors.blue),
                _slider('إحساسك بالجوع', _hunger, 1, 5, '${_hunger.round()}/5', (v) => setState(() => _hunger = v), Icons.restaurant, AppColors.teal),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: _busy ? null : _save,
                  child: _busy ? const CircularProgressIndicator(color: Colors.white) : const Text('احفظ'),
                ),
              ],
            ),
    );
  }

  Widget _slider(String label, double val, double min, double max, String display, ValueChanged<double> onChanged, IconData icon, Color color) {
    return SectionCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Icon(icon, color: color),
            const SizedBox(width: 8),
            Text(label, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            const Spacer(),
            Text(display, style: TextStyle(color: color, fontWeight: FontWeight.bold)),
          ]),
          Slider(
            value: val, min: min, max: max,
            divisions: (max - min).round() * (label.contains('نوم') ? 2 : 1),
            activeColor: color,
            onChanged: onChanged,
          ),
        ],
      ),
    );
  }
}

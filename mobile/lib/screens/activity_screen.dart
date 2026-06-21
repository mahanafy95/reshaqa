import 'package:flutter/material.dart';

import '../core/api_client.dart';
import '../core/theme.dart';
import '../services/api.dart';
import '../widgets/common.dart';

class ActivityScreen extends StatefulWidget {
  const ActivityScreen({super.key});
  @override
  State<ActivityScreen> createState() => _ActivityScreenState();
}

class _ActivityScreenState extends State<ActivityScreen> {
  List<dynamic> _list = [];
  bool _loading = true;
  String get today => DateTime.now().toIso8601String().split('T').first;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      _list = await Api.activities(today);
    } catch (_) {} finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _add() async {
    final result = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (_) => const _AddActivitySheet(),
    );
    if (result == true) _load();
  }

  Future<void> _delete(int id) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('تأكيد حذف النشاط'),
        content: const Text('متأكد إنك عايز تمسح النشاط ده؟'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('إلغاء')),
          TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('حذف', style: TextStyle(color: AppColors.danger))),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await Api.deleteActivity(id);
      _load();
    } catch (e) {
      if (!mounted) return;
      showSnack(context, ApiClient.errorMessage(e), error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('النشاط')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _add, icon: const Icon(Icons.add), label: const Text('سجّل نشاط'), backgroundColor: AppColors.orange),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(color: AppColors.orange.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(12)),
                  child: const Row(children: [
                    Icon(Icons.info_outline, color: AppColors.orange),
                    SizedBox(width: 8),
                    Expanded(child: Text('النشاط بيتسجّل لوحده وما بيتخصمش من ميزانية أكلك.', style: TextStyle(color: AppColors.orange))),
                  ]),
                ),
                const SizedBox(height: 12),
                if (_list.isEmpty)
                  const SectionCard(child: Text('مفيش نشاط متسجّل النهاردة. تحرّك شوية وسجّل 💪', textAlign: TextAlign.center))
                else
                  ..._list.map((a) => Card(
                        child: ListTile(
                          leading: const Icon(Icons.directions_run, color: AppColors.orange),
                          title: Text(a['type_ar']),
                          subtitle: Text([
                            if ((a['duration_min'] ?? 0) > 0) '${a['duration_min']} دقيقة',
                            if (a['steps'] != null) '${a['steps']} خطوة',
                            if (a['calories_burned'] != null) '${(a['calories_burned'] as num).round()} سعرة محروقة',
                          ].join(' • ')),
                          trailing: IconButton(
                            icon: const Icon(Icons.delete_outline, color: AppColors.danger),
                            onPressed: () => _delete(a['id']),
                          ),
                        ),
                      )),
              ],
            ),
    );
  }
}

class _AddActivitySheet extends StatefulWidget {
  const _AddActivitySheet();
  @override
  State<_AddActivitySheet> createState() => _AddActivitySheetState();
}

class _AddActivitySheetState extends State<_AddActivitySheet> {
  final _type = TextEditingController();
  final _dur = TextEditingController();
  final _cal = TextEditingController();
  bool _busy = false;

  static const _common = ['مشي', 'جري', 'سباحة', 'جيم', 'دراجة', 'كرة'];

  Future<void> _save() async {
    if (_type.text.trim().isEmpty) {
      showSnack(context, 'اكتب نوع النشاط الأول 🏃', error: true);
      return;
    }
    final dur = int.tryParse(_dur.text) ?? 0;
    final cal = double.tryParse(_cal.text);
    if (dur <= 0 && cal == null) {
      showSnack(context, 'ضيف المدة بالدقايق أو السعرات المحروقة', error: true);
      return;
    }
    setState(() => _busy = true);
    try {
      await Api.addActivity({
        'type_ar': _type.text.trim(),
        'duration_min': dur,
        'calories_burned': cal,
        'source': 'manual',
      });
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      if (mounted) {
        setState(() => _busy = false);
        showSnack(context, ApiClient.errorMessage(e), error: true);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom, left: 16, right: 16, top: 16),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text('سجّل نشاط', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 12),
          Wrap(spacing: 8, children: _common.map((t) => ActionChip(label: Text(t), onPressed: () => _type.text = t)).toList()),
          const SizedBox(height: 10),
          TextField(controller: _type, decoration: const InputDecoration(labelText: 'نوع النشاط')),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(child: TextField(controller: _dur, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'المدة (دقيقة)'))),
            const SizedBox(width: 8),
            Expanded(child: TextField(controller: _cal, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'سعرات محروقة (اختياري)'))),
          ]),
          const SizedBox(height: 14),
          ElevatedButton(
            onPressed: _busy ? null : _save,
            child: _busy ? const CircularProgressIndicator(color: Colors.white) : const Text('سجّل'),
          ),
          const SizedBox(height: 12),
        ],
      ),
    );
  }
}

import 'package:flutter/material.dart';

import '../core/api_client.dart';
import '../core/theme.dart';
import '../services/api.dart';
import '../widgets/common.dart';

/// مكوّن في الواجهة.
class _Ingredient {
  final name = TextEditingController();
  final grams = TextEditingController(text: '100');
  final cal100 = TextEditingController();
  final p100 = TextEditingController();
  final c100 = TextEditingController();
  final f100 = TextEditingController();
  bool isOil = false;
}

class RecipeBuilderScreen extends StatefulWidget {
  const RecipeBuilderScreen({super.key, this.recipe});

  /// لو متبعتة: بنفتح الشاشة في وضع التعديل ونملا الحقول من الوصفة الموجودة.
  final Map? recipe;

  @override
  State<RecipeBuilderScreen> createState() => _RecipeBuilderScreenState();
}

class _RecipeBuilderScreenState extends State<RecipeBuilderScreen> {
  final _name = TextEditingController();
  final _servings = TextEditingController(text: '4');
  final List<_Ingredient> _ingredients = [_Ingredient()];
  bool _busy = false;

  bool get _isEdit => widget.recipe != null;

  @override
  void initState() {
    super.initState();
    final r = widget.recipe;
    if (r == null) return;
    // وضع التعديل — نملا الحقول من الوصفة الموجودة.
    _name.text = (r['name_ar'] ?? '').toString();
    _servings.text = (r['servings'] as num?)?.toStringAsFixed(0) ?? '4';
    final ings = (r['ingredients'] as List?) ?? [];
    if (ings.isNotEmpty) {
      _ingredients
        ..clear()
        ..addAll(ings.map((raw) {
          final ing = raw as Map;
          final amount = (ing['amount'] as num?)?.toDouble() ?? 0;
          final factor = amount > 0 ? amount / 100 : 1.0;
          final e = _Ingredient();
          e.name.text = (ing['name_ar'] ?? '').toString();
          e.grams.text = amount.toStringAsFixed(0);
          e.isOil = ing['is_oil'] == true;
          // المخزّن إجمالي للكمية — نرجّعه لقيم كل 100جم عشان حقول الواجهة.
          final cal = (ing['calories'] as num?)?.toDouble() ?? 0;
          e.cal100.text = (cal > 0 && factor > 0) ? (cal / factor).round().toString() : '';
          e.p100.text = _per100(ing['protein'], factor);
          e.c100.text = _per100(ing['carbs'], factor);
          e.f100.text = _per100(ing['fat'], factor);
          return e;
        }));
    }
  }

  /// يرجّع قيمة الماكرو لكل 100جم من الإجمالي المخزّن (فاضي لو صفر).
  String _per100(dynamic total, double factor) {
    final v = (total as num?)?.toDouble() ?? 0;
    if (v <= 0 || factor <= 0) return '';
    return (v / factor).toStringAsFixed(1);
  }

  Future<void> _save() async {
    if (_name.text.trim().isEmpty) {
      showSnack(context, 'اكتب اسم الوصفة', error: true);
      return;
    }
    final ings = _ingredients.where((i) => i.name.text.trim().isNotEmpty).map((i) => {
          'name_ar': i.name.text.trim(),
          'amount_g': double.tryParse(i.grams.text) ?? 0,
          'is_oil': i.isOil,
          'per100_calories': double.tryParse(i.cal100.text) ?? 0,
          'per100_protein': double.tryParse(i.p100.text) ?? 0,
          'per100_carbs': double.tryParse(i.c100.text) ?? 0,
          'per100_fat': double.tryParse(i.f100.text) ?? 0,
        }).toList();
    if (ings.isEmpty) {
      showSnack(context, 'ضيف مكوّن واحد على الأقل', error: true);
      return;
    }
    setState(() => _busy = true);
    try {
      final body = {
        'name_ar': _name.text.trim(),
        'servings': double.tryParse(_servings.text) ?? 1,
        'ingredients': ings,
      };
      if (_isEdit) {
        await Api.updateRecipe(widget.recipe!['id'], body);
      } else {
        await Api.createRecipe(body);
      }
      if (mounted) {
        showSnack(context, _isEdit ? 'اتعدّلت الوصفة 👍' : 'اتحفظت الوصفة 👍');
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
      appBar: AppBar(title: Text(_isEdit ? 'تعديل الوصفة' : 'وصفة جديدة')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          TextField(controller: _name, decoration: const InputDecoration(labelText: 'اسم الوصفة (مثلاً: محشي والدتي)')),
          const SizedBox(height: 10),
          TextField(controller: _servings, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'عدد الأنفار (الحلة بتطلع كام نصيب)')),
          const SizedBox(height: 16),
          const Text('المكوّنات', style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold)),
          const SizedBox(height: 4),
          Text('اكتب قيم كل 100جم للمكوّن (السعرات أساسية، الماكروز اختيارية).', style: TextStyle(color: mutedColor(context), fontSize: 12)),
          const SizedBox(height: 8),
          ..._ingredients.asMap().entries.map((e) => _ingredientCard(e.key, e.value)),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: () => setState(() => _ingredients.add(_Ingredient())),
            icon: const Icon(Icons.add),
            label: const Text('أضف مكوّن'),
          ),
          const SizedBox(height: 20),
          ElevatedButton(
            onPressed: _busy ? null : _save,
            child: _busy
                ? const CircularProgressIndicator(color: Colors.white)
                : Text(_isEdit ? 'احفظ التعديلات' : 'احفظ الوصفة'),
          ),
        ],
      ),
    );
  }

  Widget _ingredientCard(int index, _Ingredient ing) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            Row(
              children: [
                Expanded(child: TextField(controller: ing.name, decoration: const InputDecoration(labelText: 'المكوّن'))),
                if (_ingredients.length > 1)
                  IconButton(icon: const Icon(Icons.delete_outline, color: AppColors.danger), onPressed: () => setState(() => _ingredients.removeAt(index))),
              ],
            ),
            const SizedBox(height: 8),
            Row(children: [
              Expanded(child: _f(ing.grams, 'الكمية (جم)')),
              const SizedBox(width: 8),
              Expanded(child: _f(ing.cal100, 'سعرة/100جم')),
            ]),
            const SizedBox(height: 8),
            Row(children: [
              Expanded(child: _f(ing.p100, 'بروتين/100')),
              const SizedBox(width: 6),
              Expanded(child: _f(ing.c100, 'نشويات/100')),
              const SizedBox(width: 6),
              Expanded(child: _f(ing.f100, 'دهون/100')),
            ]),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              dense: true,
              title: const Text('زيت / سمنة'),
              value: ing.isOil,
              onChanged: (v) => setState(() => ing.isOil = v),
            ),
          ],
        ),
      ),
    );
  }

  Widget _f(TextEditingController c, String l) => TextField(
        controller: c,
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        decoration: InputDecoration(labelText: l, isDense: true),
      );
}

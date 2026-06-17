import 'dart:async';

import 'package:flutter/material.dart';
import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import 'package:image_picker/image_picker.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../core/api_client.dart';
import '../core/theme.dart';
import '../services/api.dart';
import '../widgets/common.dart';
import 'recipe_builder_screen.dart';

class LogFoodScreen extends StatefulWidget {
  const LogFoodScreen({super.key});
  @override
  State<LogFoodScreen> createState() => _LogFoodScreenState();
}

class _LogFoodScreenState extends State<LogFoodScreen> with SingleTickerProviderStateMixin {
  late final TabController _tabs = TabController(length: 6, vsync: this);
  String _meal = 'lunch';

  static const _meals = {'breakfast': 'فطار', 'lunch': 'غدا', 'dinner': 'عشا', 'snack': 'سناك'};

  String get today => DateTime.now().toIso8601String().split('T').first;

  Future<void> confirmAndAdd({
    required String name,
    double amount = 100,
    required double calories,
    double protein = 0,
    double carbs = 0,
    double fat = 0,
    String source = 'manual',
  }) async {
    final result = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (_) => _ConfirmSheet(
        name: name, amount: amount, calories: calories, protein: protein,
        carbs: carbs, fat: fat, source: source, meal: _meal, date: today,
      ),
    );
    if (result == true && mounted) {
      showSnack(context, 'اتسجّل في $today 👍');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('تسجيل الأكل'),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(96),
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                child: Wrap(
                  spacing: 8,
                  alignment: WrapAlignment.center,
                  children: _meals.entries.map((e) => ChoiceChip(
                    label: Text(e.value),
                    selected: _meal == e.key,
                    onSelected: (_) => setState(() => _meal = e.key),
                  )).toList(),
                ),
              ),
              TabBar(
                controller: _tabs,
                isScrollable: true,
                tabAlignment: TabAlignment.center,
                tabs: const [
                  Tab(text: 'يدوي'), Tab(text: 'المكتبة'), Tab(text: 'باركود'),
                  Tab(text: 'كاميرا'), Tab(text: 'المفضلة'), Tab(text: 'وصفات'),
                ],
              ),
            ],
          ),
        ),
      ),
      body: TabBarView(
        controller: _tabs,
        children: [
          _ManualTab(onAdd: confirmAndAdd),
          _LibraryTab(onAdd: confirmAndAdd),
          _BarcodeTab(onAdd: confirmAndAdd),
          _CameraTab(onAdd: confirmAndAdd),
          _FavoritesTab(meal: _meal, date: today),
          _RecipesTab(meal: _meal, date: today),
        ],
      ),
    );
  }
}

typedef AddFn = Future<void> Function({
  required String name, double amount, required double calories,
  double protein, double carbs, double fat, String source,
});

// ============ تأكيد الإضافة ============
class _ConfirmSheet extends StatefulWidget {
  const _ConfirmSheet({required this.name, required this.amount, required this.calories,
    required this.protein, required this.carbs, required this.fat, required this.source,
    required this.meal, required this.date});
  final String name, source, meal, date;
  final double amount, calories, protein, carbs, fat;
  @override
  State<_ConfirmSheet> createState() => _ConfirmSheetState();
}

class _ConfirmSheetState extends State<_ConfirmSheet> {
  late final _name = TextEditingController(text: widget.name);
  late final _amount = TextEditingController(text: widget.amount.toStringAsFixed(0));
  late final _cal = TextEditingController(text: widget.calories.toStringAsFixed(0));
  late final _p = TextEditingController(text: widget.protein.toStringAsFixed(1));
  late final _c = TextEditingController(text: widget.carbs.toStringAsFixed(1));
  late final _f = TextEditingController(text: widget.fat.toStringAsFixed(1));
  bool _busy = false;

  // القيم الأولية لإعادة الحساب تناسبياً مع الجرامات
  late final double _baseAmount = widget.amount > 0 ? widget.amount : 100;
  late final double _baseCal = widget.calories;
  late final double _baseP = widget.protein;
  late final double _baseC = widget.carbs;
  late final double _baseF = widget.fat;

  /// يعيد حساب السعرات والماكروز نسبةً للجرامات الجديدة (مش ثابت 100جم).
  void _recomputeFromAmount(String value) {
    final newAmount = double.tryParse(value);
    if (newAmount == null || newAmount <= 0 || _baseAmount <= 0) return;
    final factor = newAmount / _baseAmount;
    setState(() {
      _cal.text = (_baseCal * factor).round().toString();
      _p.text = (_baseP * factor).toStringAsFixed(1);
      _c.text = (_baseC * factor).toStringAsFixed(1);
      _f.text = (_baseF * factor).toStringAsFixed(1);
    });
  }

  Future<void> _save() async {
    setState(() => _busy = true);
    try {
      await Api.addFood({
        'date': widget.date, 'meal': widget.meal, 'name_ar': _name.text.trim(),
        'amount': double.tryParse(_amount.text) ?? 100,
        'calories': double.tryParse(_cal.text) ?? 0,
        'protein': double.tryParse(_p.text) ?? 0,
        'carbs': double.tryParse(_c.text) ?? 0,
        'fat': double.tryParse(_f.text) ?? 0,
        'source': widget.source,
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
          const Text('تأكيد وتعديل', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 12),
          TextField(controller: _name, decoration: const InputDecoration(labelText: 'الاسم')),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(
              child: TextField(
                controller: _amount,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                onChanged: _recomputeFromAmount,
                decoration: const InputDecoration(labelText: 'الكمية (جم)', helperText: 'غيّرها وتتحسب تلقائياً'),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(child: _f2(_cal, 'سعرات')),
          ]),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(child: _f2(_p, 'بروتين')),
            const SizedBox(width: 8),
            Expanded(child: _f2(_c, 'نشويات')),
            const SizedBox(width: 8),
            Expanded(child: _f2(_f, 'دهون')),
          ]),
          const SizedBox(height: 14),
          ElevatedButton(
            onPressed: _busy ? null : _save,
            child: _busy ? const CircularProgressIndicator(color: Colors.white) : const Text('أضف للوجبة'),
          ),
          const SizedBox(height: 12),
        ],
      ),
    );
  }

  Widget _f2(TextEditingController c, String l) => TextField(
    controller: c, keyboardType: const TextInputType.numberWithOptions(decimal: true),
    decoration: InputDecoration(labelText: l));
}

// ============ يدوي + تقدير + اقتراح ============
class _ManualTab extends StatefulWidget {
  const _ManualTab({required this.onAdd});
  final AddFn onAdd;
  @override
  State<_ManualTab> createState() => _ManualTabState();
}

class _ManualTabState extends State<_ManualTab> {
  final _name = TextEditingController();
  final _amount = TextEditingController(text: '100');
  List<dynamic> _suggestions = [];
  Timer? _debounce;
  bool _estimating = false;

  void _onNameChanged(String q) {
    _debounce?.cancel();
    if (q.trim().length < 2) {
      setState(() => _suggestions = []);
      return;
    }
    _debounce = Timer(const Duration(milliseconds: 350), () async {
      try {
        final r = await Api.suggest(q.trim());
        if (mounted) setState(() => _suggestions = r);
      } catch (_) {}
    });
  }

  Future<void> _estimate() async {
    if (_name.text.trim().isEmpty) return;
    setState(() => _estimating = true);
    try {
      final amount = double.tryParse(_amount.text) ?? 100;
      final r = await Api.estimate(_name.text.trim(), amount);
      await widget.onAdd(
        name: r['name_ar'], amount: amount, calories: (r['calories'] as num).toDouble(),
        protein: (r['protein'] as num).toDouble(), carbs: (r['carbs'] as num).toDouble(),
        fat: (r['fat'] as num).toDouble(), source: r['source'] ?? 'estimated',
      );
    } catch (e) {
      if (mounted) showSnack(context, ApiClient.errorMessage(e), error: true);
    } finally {
      if (mounted) setState(() => _estimating = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        TextField(
          controller: _name,
          onChanged: _onNameChanged,
          decoration: const InputDecoration(labelText: 'اسم الأكلة', prefixIcon: Icon(Icons.search)),
        ),
        const SizedBox(height: 10),
        TextField(
          controller: _amount,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(labelText: 'الكمية (جرام)'),
        ),
        const SizedBox(height: 12),
        Row(children: [
          Expanded(
            child: OutlinedButton.icon(
              onPressed: _estimating ? null : _estimate,
              icon: const Icon(Icons.auto_awesome),
              label: Text(_estimating ? '...' : 'قدّر السعرات تلقائياً'),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: ElevatedButton(
              onPressed: () => widget.onAdd(name: _name.text.trim().isEmpty ? 'أكلة' : _name.text.trim(),
                  amount: double.tryParse(_amount.text) ?? 100, calories: 0, source: 'manual'),
              child: const Text('إدخال يدوي'),
            ),
          ),
        ]),
        if (_suggestions.isNotEmpty) ...[
          const SizedBox(height: 12),
          const Align(alignment: Alignment.centerRight, child: Text('اقتراحات:', style: TextStyle(fontWeight: FontWeight.bold))),
          ..._suggestions.map((s) => Card(
            child: ListTile(
              title: Text(s['name_ar']),
              subtitle: Text(s['kind'] == 'library'
                  ? '${s['calories_per_100']} سعرة/100جم'
                  : '${s['calories_per_serving'] ?? ''} سعرة'),
              trailing: const Icon(Icons.add_circle_outline),
              onTap: () {
                final per100 = (s['calories_per_100'] as num?)?.toDouble();
                final perServ = (s['calories_per_serving'] as num?)?.toDouble();
                final amount = double.tryParse(_amount.text) ?? 100;
                final cal = per100 != null ? per100 * amount / 100 : (perServ ?? 0);
                widget.onAdd(name: s['name_ar'], amount: amount, calories: cal, source: 'library');
              },
            ),
          )),
        ],
      ],
    );
  }
}

// ============ المكتبة ============
class _LibraryTab extends StatefulWidget {
  const _LibraryTab({required this.onAdd});
  final AddFn onAdd;
  @override
  State<_LibraryTab> createState() => _LibraryTabState();
}

class _LibraryTabState extends State<_LibraryTab> {
  final _q = TextEditingController();
  List<dynamic> _results = [];
  bool _loading = false;
  Timer? _debounce;

  void _search(String q) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 350), () async {
      setState(() => _loading = true);
      try {
        _results = await Api.librarySearch(q.trim());
      } catch (_) {} finally {
        if (mounted) setState(() => _loading = false);
      }
    });
  }

  @override
  void initState() {
    super.initState();
    _search('');
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(16),
          child: TextField(
            controller: _q,
            onChanged: _search,
            decoration: const InputDecoration(labelText: 'ابحث في المكتبة', prefixIcon: Icon(Icons.search)),
          ),
        ),
        if (_loading) const LinearProgressIndicator(),
        Expanded(
          child: ListView.builder(
            itemCount: _results.length,
            itemBuilder: (_, i) {
              final f = _results[i];
              return Card(
                margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                child: ListTile(
                  title: Text(f['name_ar']),
                  subtitle: Text('${f['calories_per_100']} سعرة / 100جم'),
                  trailing: const Icon(Icons.add_circle_outline, color: AppColors.teal),
                  onTap: () => widget.onAdd(
                    name: f['name_ar'],
                    amount: (f['household_grams'] as num?)?.toDouble() ?? 100,
                    calories: (f['calories_per_100'] as num).toDouble() * (((f['household_grams'] as num?)?.toDouble() ?? 100) / 100),
                    protein: (f['protein'] as num).toDouble() * (((f['household_grams'] as num?)?.toDouble() ?? 100) / 100),
                    carbs: (f['carbs'] as num).toDouble() * (((f['household_grams'] as num?)?.toDouble() ?? 100) / 100),
                    fat: (f['fat'] as num).toDouble() * (((f['household_grams'] as num?)?.toDouble() ?? 100) / 100),
                    source: 'library',
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}

// ============ باركود ============
class _BarcodeTab extends StatelessWidget {
  const _BarcodeTab({required this.onAdd});
  final AddFn onAdd;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.qr_code_scanner, size: 80, color: AppColors.teal),
            const SizedBox(height: 16),
            const Text('امسح باركود المنتج عشان نجيب قيمه الغذائية', textAlign: TextAlign.center),
            const SizedBox(height: 20),
            ElevatedButton.icon(
              icon: const Icon(Icons.camera_alt),
              label: const Text('افتح الماسح'),
              onPressed: () async {
                final code = await Navigator.push<String>(context, MaterialPageRoute(builder: (_) => const _ScannerScreen()));
                if (code == null || !context.mounted) return;
                try {
                  final r = await Api.barcode(code);
                  await onAdd(name: r['name_ar'], amount: 100,
                      calories: (r['calories_per_100'] as num).toDouble(),
                      protein: (r['protein'] as num).toDouble(), carbs: (r['carbs'] as num).toDouble(),
                      fat: (r['fat'] as num).toDouble(), source: 'barcode');
                } catch (e) {
                  if (context.mounted) showSnack(context, ApiClient.errorMessage(e), error: true);
                }
              },
            ),
          ],
        ),
      ),
    );
  }
}

class _ScannerScreen extends StatelessWidget {
  const _ScannerScreen();
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('امسح الباركود')),
      body: MobileScanner(
        onDetect: (capture) {
          final code = capture.barcodes.firstOrNull?.rawValue;
          if (code != null) Navigator.pop(context, code);
        },
      ),
    );
  }
}

// ============ كاميرا OCR ============
class _CameraTab extends StatefulWidget {
  const _CameraTab({required this.onAdd});
  final AddFn onAdd;
  @override
  State<_CameraTab> createState() => _CameraTabState();
}

class _CameraTabState extends State<_CameraTab> {
  bool _busy = false;

  Future<void> _scanLabel() async {
    setState(() => _busy = true);
    try {
      final picker = ImagePicker();
      final img = await picker.pickImage(source: ImageSource.camera, imageQuality: 85);
      if (img == null) {
        setState(() => _busy = false);
        return;
      }
      final recognizer = TextRecognizer(script: TextRecognitionScript.latin);
      final recognized = await recognizer.processImage(InputImage.fromFilePath(img.path));
      await recognizer.close();
      final r = await Api.parseLabel(recognized.text);
      final cal = (r['calories'] as num?)?.toDouble() ?? 0;
      if (!mounted) return;
      await widget.onAdd(
        name: 'منتج (من الملصق)', amount: 100, calories: cal,
        protein: (r['protein'] as num?)?.toDouble() ?? 0,
        carbs: (r['carbs'] as num?)?.toDouble() ?? 0,
        fat: (r['fat'] as num?)?.toDouble() ?? 0, source: 'label',
      );
    } catch (e) {
      if (mounted) showSnack(context, ApiClient.errorMessage(e), error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.document_scanner, size: 80, color: AppColors.teal),
            const SizedBox(height: 16),
            const Text('صوّر جدول التغذية على المنتج ونستخرجلك القيم', textAlign: TextAlign.center),
            const SizedBox(height: 20),
            ElevatedButton.icon(
              icon: const Icon(Icons.camera_alt),
              label: Text(_busy ? 'بنحلّل...' : 'صوّر الملصق'),
              onPressed: _busy ? null : _scanLabel,
            ),
          ],
        ),
      ),
    );
  }
}

// ============ المفضلة ============
class _FavoritesTab extends StatefulWidget {
  const _FavoritesTab({required this.meal, required this.date});
  final String meal, date;
  @override
  State<_FavoritesTab> createState() => _FavoritesTabState();
}

class _FavoritesTabState extends State<_FavoritesTab> {
  List<dynamic> _favs = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      _favs = await Api.favorites();
    } catch (_) {} finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_favs.isEmpty) return const Center(child: Text('لسه مفيش مفضلات. ضيف أكلاتك المتكررة هنا للإضافة السريعة 🙂'));
    return ListView.builder(
      padding: const EdgeInsets.all(12),
      itemCount: _favs.length,
      itemBuilder: (_, i) {
        final f = _favs[i];
        return Card(
          child: ListTile(
            leading: const Icon(Icons.star, color: AppColors.orange),
            title: Text(f['name_ar']),
            subtitle: Text('${f['calories']} سعرة'),
            trailing: const Icon(Icons.add_circle, color: AppColors.teal),
            onTap: () async {
              try {
                await Api.logFavorite(f['id'], {'date': widget.date, 'meal': widget.meal});
                if (context.mounted) showSnack(context, 'اتسجّل 👍');
              } catch (e) {
                if (context.mounted) showSnack(context, ApiClient.errorMessage(e), error: true);
              }
            },
          ),
        );
      },
    );
  }
}

// ============ الوصفات ============
class _RecipesTab extends StatefulWidget {
  const _RecipesTab({required this.meal, required this.date});
  final String meal, date;
  @override
  State<_RecipesTab> createState() => _RecipesTabState();
}

class _RecipesTabState extends State<_RecipesTab> {
  List<dynamic> _recipes = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      _recipes = await Api.recipes();
    } catch (_) {} finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _logPortion(Map recipe) async {
    final servings = await showDialog<double>(
      context: context,
      builder: (_) => const _ServingsDialog(),
    );
    if (servings == null || !mounted) return;
    try {
      await Api.logRecipe(recipe['id'], {'date': widget.date, 'meal': widget.meal, 'servings': servings});
      if (context.mounted) showSnack(context, 'اتسجّل نصيبك 👍');
    } catch (e) {
      if (context.mounted) showSnack(context, ApiClient.errorMessage(e), error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      floatingActionButton: FloatingActionButton.small(
        backgroundColor: AppColors.teal,
        onPressed: () async {
          await Navigator.push(context, MaterialPageRoute(builder: (_) => const RecipeBuilderScreen()));
          _load();
        },
        child: const Icon(Icons.add),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _recipes.isEmpty
              ? const Center(child: Text('لسه مفيش وصفات. اعمل وصفتك بالزرار 👇'))
              : ListView.builder(
                  padding: const EdgeInsets.all(12),
                  itemCount: _recipes.length,
                  itemBuilder: (_, i) {
                    final r = _recipes[i];
                    return Card(
                      child: ListTile(
                        leading: const Icon(Icons.soup_kitchen, color: AppColors.teal),
                        title: Text(r['name_ar']),
                        subtitle: Text('${r['servings']} أنفار • نصيب الفرد ${r['per_serving_calories']} سعرة'),
                        trailing: const Icon(Icons.add_circle, color: AppColors.teal),
                        onTap: () => _logPortion(r),
                      ),
                    );
                  },
                ),
    );
  }
}

class _ServingsDialog extends StatefulWidget {
  const _ServingsDialog();
  @override
  State<_ServingsDialog> createState() => _ServingsDialogState();
}

class _ServingsDialogState extends State<_ServingsDialog> {
  final _c = TextEditingController(text: '1');
  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('كام نصيب؟'),
      content: TextField(
        controller: _c,
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        decoration: const InputDecoration(labelText: 'عدد الأنفار'),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('إلغاء')),
        ElevatedButton(onPressed: () => Navigator.pop(context, double.tryParse(_c.text) ?? 1), child: const Text('سجّل')),
      ],
    );
  }
}

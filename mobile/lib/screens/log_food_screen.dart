import 'dart:async';

import 'package:flutter/material.dart';
import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import 'package:image_picker/image_picker.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/theme.dart';
import '../core/units.dart';
import '../services/api.dart';
import '../state/app_state.dart';
import '../widgets/common.dart';
import 'meal_chat_tab.dart';
import 'paywall_screen.dart';
import 'recipe_builder_screen.dart';
import 'reports_screen.dart' show PremiumLock;

class LogFoodScreen extends StatefulWidget {
  const LogFoodScreen({super.key});
  @override
  State<LogFoodScreen> createState() => _LogFoodScreenState();
}

class _LogFoodScreenState extends State<LogFoodScreen> with SingleTickerProviderStateMixin {
  late final TabController _tabs = TabController(length: 7, vsync: this);
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
                  Tab(text: '🤖 مساعد'), Tab(text: 'يدوي'), Tab(text: 'المكتبة'), Tab(text: 'باركود'),
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
          MealChatLauncher(meal: _meal, date: today, onLogged: () => showSnack(context, 'اتحدّث يومك 👍')),
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
  String _unit = 'g';
  String _sugarKey = 'none';
  final _sugarQty = TextEditingController(text: '1');
  String _sugarUnit = 'tsp';
  Map<String, double>? _per100; // cal,p,c,f لكل 100
  List<dynamic> _suggestions = [];
  Timer? _debounce;
  bool _estimating = false;

  double get _grams => toGrams(double.tryParse(_amount.text) ?? 0, _unit);
  double get _sugarG => _sugarKey == 'none' ? 0 : (double.tryParse(_sugarQty.text) ?? 0) * sugarUnitByKey(_sugarUnit).grams;
  int get _sugarCal => (_sugarG * sugarByKey(_sugarKey).calPerG).round();
  int get _previewCal {
    final base = _per100 == null ? 0.0 : _per100!['cal']! * _grams / 100;
    return (base + _sugarCal).round();
  }

  // أول ما تكتب الصنف: اقتراحات + جلب السعرات تلقائياً (قيم لكل 100)
  void _onNameChanged(String q) {
    _debounce?.cancel();
    final t = q.trim();
    if (t.length < 2) {
      setState(() {
        _suggestions = [];
        _per100 = null;
      });
      return;
    }
    setState(() => _estimating = true);
    _debounce = Timer(const Duration(milliseconds: 450), () async {
      try {
        final s = await Api.suggest(t);
        if (mounted) setState(() => _suggestions = s);
      } catch (_) {}
      try {
        final r = await Api.estimate(t, 100);
        if (mounted) {
          setState(() => _per100 = {
                'cal': (r['calories'] as num).toDouble(),
                'p': (r['protein'] as num).toDouble(),
                'c': (r['carbs'] as num).toDouble(),
                'f': (r['fat'] as num).toDouble(),
              });
        }
      } catch (_) {}
      if (mounted) setState(() => _estimating = false);
    });
  }

  Future<void> _add() async {
    final grams = _grams;
    double cal = 0, p = 0, c = 0, f = 0;
    if (_per100 != null) {
      final fct = grams / 100;
      cal = _per100!['cal']! * fct;
      p = _per100!['p']! * fct;
      c = _per100!['c']! * fct;
      f = _per100!['f']! * fct;
    } else if (_name.text.trim().isNotEmpty) {
      try {
        final r = await Api.estimate(_name.text.trim(), grams);
        cal = (r['calories'] as num).toDouble();
        p = (r['protein'] as num).toDouble();
        c = (r['carbs'] as num).toDouble();
        f = (r['fat'] as num).toDouble();
      } catch (_) {}
    }
    final sugar = sugarByKey(_sugarKey);
    final sCal = _sugarG * sugar.calPerG;
    final sCarb = _sugarG * sugar.carbPerG;
    var nm = _name.text.trim().isEmpty ? 'صنف' : _name.text.trim();
    final qv = double.tryParse(_amount.text) ?? 0;
    if (_unit != 'g') nm = '$nm (${unitText(qv, _unit)})';
    if (_sugarKey != 'none') nm = '$nm + ${sugar.label}';
    await widget.onAdd(
      name: nm,
      amount: grams + _sugarG,
      calories: cal + sCal,
      protein: p,
      carbs: c + sCarb,
      fat: f,
      source: _per100 != null ? 'library' : 'manual',
    );
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        TextField(
          controller: _name,
          onChanged: _onNameChanged,
          decoration: InputDecoration(
            labelText: 'اسم الصنف (السعرات تتجاب لوحدها)',
            prefixIcon: const Icon(Icons.search),
            suffix: _estimating ? Text('بنحسب…', style: TextStyle(fontSize: 11, color: mutedColor(context))) : null,
          ),
        ),
        const SizedBox(height: 10),
        Row(children: [
          Expanded(
            child: TextField(
              controller: _amount,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              onChanged: (_) => setState(() {}),
              decoration: const InputDecoration(labelText: 'الكمية'),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: DropdownButtonFormField<String>(
              initialValue: _unit,
              decoration: const InputDecoration(labelText: 'الوحدة'),
              items: foodUnits.map((u) => DropdownMenuItem(value: u.key, child: Text(u.label))).toList(),
              onChanged: (v) => setState(() => _unit = v ?? 'g'),
            ),
          ),
        ]),
        const SizedBox(height: 10),
        Row(children: [
          Expanded(
            child: DropdownButtonFormField<String>(
              initialValue: _sugarKey,
              decoration: const InputDecoration(labelText: '🍬 سكر/محلّي'),
              items: sugarTypes.map((s) => DropdownMenuItem(value: s.key, child: Text(s.label, overflow: TextOverflow.ellipsis))).toList(),
              onChanged: (v) => setState(() => _sugarKey = v ?? 'none'),
            ),
          ),
          if (_sugarKey != 'none') ...[
            const SizedBox(width: 8),
            SizedBox(
              width: 64,
              child: TextField(
                controller: _sugarQty,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                onChanged: (_) => setState(() {}),
                decoration: const InputDecoration(labelText: 'عدد'),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: DropdownButtonFormField<String>(
                initialValue: _sugarUnit,
                decoration: const InputDecoration(labelText: 'وحدة'),
                items: sugarUnits.map((u) => DropdownMenuItem(value: u.key, child: Text(u.label, overflow: TextOverflow.ellipsis))).toList(),
                onChanged: (v) => setState(() => _sugarUnit = v ?? 'tsp'),
              ),
            ),
          ],
        ]),
        const SizedBox(height: 12),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(color: AppColors.teal.withValues(alpha: 0.07), borderRadius: BorderRadius.circular(12)),
          child: Column(children: [
            Text('$_previewCal', style: const TextStyle(fontSize: 26, fontWeight: FontWeight.bold, color: AppColors.teal)),
            Text('سعرة لـ ${unitText(double.tryParse(_amount.text) ?? 0, _unit)}${_sugarCal > 0 ? ' + $_sugarCal سكر' : ''}',
                style: TextStyle(color: mutedColor(context), fontSize: 12)),
          ]),
        ),
        const SizedBox(height: 12),
        ElevatedButton.icon(
          style: ElevatedButton.styleFrom(minimumSize: const Size.fromHeight(50)),
          onPressed: _add,
          icon: const Icon(Icons.auto_awesome),
          label: const Text('أضف للوجبة'),
        ),
        if (_suggestions.isNotEmpty) ...[
          const SizedBox(height: 12),
          const Align(alignment: Alignment.centerRight, child: Text('اقتراحات:', style: TextStyle(fontWeight: FontWeight.bold))),
          ..._suggestions.map((s) => Card(
                child: ListTile(
                  title: Text(s['name_ar']),
                  subtitle: Text(s['kind'] == 'library' ? '${s['calories_per_100']} سعرة/100جم' : '${s['calories_per_serving'] ?? ''} سعرة'),
                  trailing: const Icon(Icons.add_circle_outline),
                  onTap: () {
                    final per100 = (s['calories_per_100'] as num?)?.toDouble();
                    setState(() {
                      _name.text = s['name_ar'];
                      _suggestions = [];
                      if (per100 != null) {
                        _per100 = {'cal': per100, 'p': 0, 'c': 0, 'f': 0};
                      }
                    });
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
class _BarcodeTab extends StatefulWidget {
  const _BarcodeTab({required this.onAdd});
  final AddFn onAdd;

  @override
  State<_BarcodeTab> createState() => _BarcodeTabState();
}

class _BarcodeTabState extends State<_BarcodeTab> {
  bool _busy = false;

  @override
  Widget build(BuildContext context) {
    // مسح الباركود ميزة Premium — نوضّح ده للمستخدم المجاني بدل ما يحس إنه عطل.
    final isPremium = context.watch<AppState>().isPremium;
    if (!isPremium) {
      return const PremiumLock(
        title: 'مسح الباركود ميزة Premium 💎',
        message: 'مسح باركود المنتج وجلب قيمه الغذائية تلقائياً من مميزات الاشتراك. '
            'اشترك عشان تفتحها — أو سجّل أكلك بالكتابة أو يدوي، ده مجاني تماماً ✅',
      );
    }
    return Stack(
      children: [
        Center(
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
                  onPressed: _busy ? null : _scanAndHandle,
                ),
                const SizedBox(height: 8),
                Text('لو المنتج مش موجود، هنطلب قيمه مرة واحدة ونفتكره ليك بعد كده 👌',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: mutedColor(context), fontSize: 12)),
              ],
            ),
          ),
        ),
        if (_busy)
          const Positioned.fill(
            child: ColoredBox(
              color: Colors.black45,
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    CircularProgressIndicator(color: Colors.white),
                    SizedBox(height: 12),
                    Text('بدوّر على المنتج…', style: TextStyle(color: Colors.white)),
                  ],
                ),
              ),
            ),
          ),
      ],
    );
  }

  // ملاحظة: نستخدم سياق الـ State (الثابت) و mounted الموثوق — مش سياق مُمرَّر بيبور
  // بعد ما الكاميرا تفتح وترجع (lifecycle)، وده كان بيخلّي المسح ميرجّعش أي نتيجة.
  Future<void> _scanAndHandle() async {
    final code = await Navigator.of(context).push<String>(
        MaterialPageRoute(builder: (_) => const _ScannerScreen()));
    if (code == null || !mounted) return;
    final messenger = ScaffoldMessenger.of(context);
    setState(() => _busy = true);
    try {
      final r = await Api.barcode(code);
      if (!mounted) return;
      await widget.onAdd(
        name: (r['name_ar'] ?? 'منتج').toString(), amount: 100,
        calories: (r['calories_per_100'] as num?)?.toDouble() ?? 0,
        protein: (r['protein'] as num?)?.toDouble() ?? 0,
        carbs: (r['carbs'] as num?)?.toDouble() ?? 0,
        fat: (r['fat'] as num?)?.toDouble() ?? 0,
        source: 'barcode',
      );
    } catch (e) {
      if (!mounted) return;
      final st = ApiClient.statusOf(e);
      if (st == 402) {
        Navigator.of(context).push(MaterialPageRoute(builder: (_) => const PaywallScreen()));
      } else if (st == 404) {
        await _promptSaveProduct(code);
      } else {
        messenger.showSnackBar(SnackBar(
          content: Text(ApiClient.errorMessage(e)),
          backgroundColor: AppColors.orange,
        ));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _promptSaveProduct(String code) async {
    final saved = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (_) => _SaveBarcodeDialog(code: code),
    );
    if (saved == null || !mounted) return;
    try {
      await Api.saveBarcode(saved);
      if (!mounted) return;
      await widget.onAdd(
        name: saved['name_ar'], amount: 100,
        calories: (saved['calories_per_100'] as num).toDouble(),
        protein: (saved['protein'] as num).toDouble(),
        carbs: (saved['carbs'] as num).toDouble(),
        fat: (saved['fat'] as num).toDouble(),
        source: 'barcode',
      );
      if (mounted) showSnack(context, 'حفظنا المنتج 👌 هيتعرف عليه أي مسح جاي');
    } catch (e) {
      if (mounted) showSnack(context, ApiClient.errorMessage(e), error: true);
    }
  }
}

/// نافذة إدخال قيم منتج جديد لحفظه بالباركود (القيم لكل 100 جم/مل).
class _SaveBarcodeDialog extends StatefulWidget {
  const _SaveBarcodeDialog({required this.code});
  final String code;
  @override
  State<_SaveBarcodeDialog> createState() => _SaveBarcodeDialogState();
}

class _SaveBarcodeDialogState extends State<_SaveBarcodeDialog> {
  final _name = TextEditingController();
  final _cal = TextEditingController();
  final _carbs = TextEditingController();
  final _protein = TextEditingController();
  final _fat = TextEditingController();

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('منتج جديد'),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Text('الباركود: ${widget.code}',
              style: TextStyle(color: mutedColor(context), fontSize: 12)),
          const SizedBox(height: 4),
          Text('اكتب القيم لكل 100 جم/مل (من جدول التغذية على المنتج)',
              style: TextStyle(color: mutedColor(context), fontSize: 12)),
          TextField(controller: _name, decoration: const InputDecoration(labelText: 'اسم المنتج')),
          _numField(_cal, 'سعرات / 100'),
          _numField(_carbs, 'نشويات / 100 (اختياري)'),
          _numField(_protein, 'بروتين / 100 (اختياري)'),
          _numField(_fat, 'دهون / 100 (اختياري)'),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('إلغاء')),
        ElevatedButton(
          onPressed: () {
            final name = _name.text.trim();
            final cal = double.tryParse(_cal.text);
            if (name.isEmpty || cal == null) {
              showSnack(context, 'اكتب الاسم والسعرات على الأقل', error: true);
              return;
            }
            Navigator.pop(context, {
              'barcode': widget.code,
              'name_ar': name,
              'calories_per_100': cal,
              'carbs': double.tryParse(_carbs.text) ?? 0,
              'protein': double.tryParse(_protein.text) ?? 0,
              'fat': double.tryParse(_fat.text) ?? 0,
            });
          },
          child: const Text('احفظ'),
        ),
      ],
    );
  }

  Widget _numField(TextEditingController c, String label) => TextField(
        controller: c,
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        decoration: InputDecoration(labelText: label),
      );
}

class _ScannerScreen extends StatefulWidget {
  const _ScannerScreen();
  @override
  State<_ScannerScreen> createState() => _ScannerScreenState();
}

class _ScannerScreenState extends State<_ScannerScreen> {
  bool _handled = false; // عشان نمنع pop مرتين

  void _returnCode(String code) {
    if (_handled || !mounted) return;
    _handled = true;
    Navigator.pop(context, code);
  }

  Future<void> _manualEntry() async {
    final controller = TextEditingController();
    final code = await showDialog<String>(
      context: context,
      builder: (dialogCtx) => AlertDialog(
        title: const Text('إدخال الباركود يدويًا'),
        content: TextField(
          controller: controller,
          autofocus: true,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(labelText: 'رقم الباركود'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialogCtx), child: const Text('إلغاء')),
          ElevatedButton(
            onPressed: () {
              final c = controller.text.trim();
              Navigator.pop(dialogCtx, c.isEmpty ? null : c);
            },
            child: const Text('تأكيد'),
          ),
        ],
      ),
    );
    if (code != null && code.isNotEmpty) _returnCode(code);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('امسح الباركود'),
        actions: [
          IconButton(
            icon: const Icon(Icons.keyboard),
            tooltip: 'إدخال يدوي',
            onPressed: _manualEntry,
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: MobileScanner(
              onDetect: (capture) {
                try {
                  final code = capture.barcodes.firstOrNull?.rawValue;
                  if (code != null && code.isNotEmpty) _returnCode(code);
                } catch (_) {
                  // التقاط فاسد — نتجاهله ونكمل المسح بدل ما نكراش
                }
              },
              errorBuilder: (context, error, child) {
                return Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.no_photography, size: 64, color: mutedColor(context)),
                        const SizedBox(height: 16),
                        const Text(
                          'مقدرناش نفتح الكاميرا. اتأكد إنك سمحت بصلاحية الكاميرا، أو دخّل الباركود يدويًا.',
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 20),
                        ElevatedButton.icon(
                          icon: const Icon(Icons.keyboard),
                          label: const Text('إدخال الباركود يدويًا'),
                          onPressed: _manualEntry,
                        ),
                        const SizedBox(height: 8),
                        TextButton(
                          onPressed: () => Navigator.pop(context),
                          child: const Text('رجوع'),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: OutlinedButton.icon(
                style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(48)),
                icon: const Icon(Icons.keyboard),
                label: const Text('إدخال الباركود يدويًا'),
                onPressed: _manualEntry,
              ),
            ),
          ),
        ],
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
        if (mounted) setState(() => _busy = false);
        return;
      }

      Map<String, dynamic>? result;

      // 1) الذكاء الاصطناعي يقرا الصورة مباشرة (عربي + إنجليزي).
      try {
        final r = await Api.labelImage(img.path);
        if (((r['calories'] as num?)?.toDouble() ?? 0) > 0) {
          result = r;
        }
      } catch (_) {
        // الـ AI مش متاح أو فشل — نكمل على ML Kit
      }

      // 2) لو الـ AI رجّع صفر/فشل: نرجع لمسار ML Kit (لاتيني فقط).
      if (result == null) {
        try {
          final recognizer = TextRecognizer(script: TextRecognitionScript.latin);
          final recognized = await recognizer.processImage(InputImage.fromFilePath(img.path));
          await recognizer.close();
          if (recognized.text.trim().isNotEmpty) {
            final r = await Api.parseLabel(recognized.text);
            if (((r['calories'] as num?)?.toDouble() ?? 0) > 0) {
              result = r;
            }
          }
        } catch (_) {
          // فشل OCR — هنعرض رسالة واضحة تحت
        }
      }

      if (!mounted) return;

      final cal = (result?['calories'] as num?)?.toDouble() ?? 0;
      if (result == null || cal <= 0) {
        showSnack(context,
            'مقدرناش نقرا الملصق — جرّب صورة أوضح أو دخّل القيم يدويًا', error: true);
        return;
      }

      await widget.onAdd(
        name: 'منتج (من الملصق)', amount: 100, calories: cal,
        protein: (result['protein'] as num?)?.toDouble() ?? 0,
        carbs: (result['carbs'] as num?)?.toDouble() ?? 0,
        fat: (result['fat'] as num?)?.toDouble() ?? 0, source: 'label',
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
    setState(() => _loading = true);
    try {
      _favs = await Api.favorites();
    } catch (_) {} finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _addFavorite() async {
    final body = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (_) => const _AddFavoriteDialog(),
    );
    if (body == null || !mounted) return;
    try {
      await Api.addFavorite(body);
      if (!mounted) return;
      showSnack(context, 'اتضافت للمفضلة 👍');
      _load();
    } catch (e) {
      if (mounted) showSnack(context, ApiClient.errorMessage(e), error: true);
    }
  }

  Future<void> _deleteFavorite(Map f) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('حذف من المفضلة؟'),
        content: Text('هتشيل «${f['name_ar']}» من المفضلة.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('إلغاء')),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.danger),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('احذف'),
          ),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    try {
      await Api.deleteFavorite(f['id']);
      if (!mounted) return;
      showSnack(context, 'اتحذفت من المفضلة 👍');
      _load();
    } catch (e) {
      if (mounted) showSnack(context, ApiClient.errorMessage(e), error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: AppColors.teal,
        onPressed: _addFavorite,
        icon: const Icon(Icons.add),
        label: const Text('أضف للمفضلة'),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _favs.isEmpty
              ? const Center(child: Text('لسه مفيش مفضلات. ضيف أكلاتك المتكررة هنا للإضافة السريعة 🙂'))
              : ListView.builder(
                  padding: const EdgeInsets.all(12),
                  itemCount: _favs.length,
                  itemBuilder: (_, i) {
                    final f = _favs[i];
                    return Dismissible(
                      key: ValueKey(f['id']),
                      direction: DismissDirection.endToStart,
                      confirmDismiss: (_) async {
                        await _deleteFavorite(f);
                        return false;
                      },
                      background: Container(
                        alignment: Alignment.centerLeft,
                        padding: const EdgeInsets.only(left: 24),
                        decoration: BoxDecoration(color: AppColors.danger, borderRadius: BorderRadius.circular(12)),
                        child: const Icon(Icons.delete, color: Colors.white),
                      ),
                      child: Card(
                        child: ListTile(
                          leading: const Icon(Icons.star, color: AppColors.orange),
                          title: Text(f['name_ar']),
                          subtitle: Text('${f['calories']} سعرة'),
                          trailing: const Icon(Icons.add_circle, color: AppColors.teal),
                          onLongPress: () => _deleteFavorite(f),
                          onTap: () async {
                            try {
                              await Api.logFavorite(f['id'], {'date': widget.date, 'meal': widget.meal});
                              if (context.mounted) showSnack(context, 'اتسجّل 👍');
                            } catch (e) {
                              if (context.mounted) showSnack(context, ApiClient.errorMessage(e), error: true);
                            }
                          },
                        ),
                      ),
                    );
                  },
                ),
    );
  }
}

/// نافذة إضافة عنصر مخصّص للمفضلة (اسم + سعرات، والماكروز اختيارية).
class _AddFavoriteDialog extends StatefulWidget {
  const _AddFavoriteDialog();
  @override
  State<_AddFavoriteDialog> createState() => _AddFavoriteDialogState();
}

class _AddFavoriteDialogState extends State<_AddFavoriteDialog> {
  final _name = TextEditingController();
  final _cal = TextEditingController();
  final _protein = TextEditingController();
  final _carbs = TextEditingController();
  final _fat = TextEditingController();

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('أضف للمفضلة'),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Text('اكتب أكلتك المتكررة عشان تسجّلها بضغطة واحدة بعد كده',
              style: TextStyle(color: mutedColor(context), fontSize: 12)),
          TextField(controller: _name, decoration: const InputDecoration(labelText: 'الاسم')),
          _numField(_cal, 'سعرات'),
          _numField(_protein, 'بروتين (اختياري)'),
          _numField(_carbs, 'نشويات (اختياري)'),
          _numField(_fat, 'دهون (اختياري)'),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('إلغاء')),
        ElevatedButton(
          onPressed: () {
            final name = _name.text.trim();
            final cal = double.tryParse(_cal.text);
            if (name.isEmpty || cal == null) {
              showSnack(context, 'اكتب الاسم والسعرات على الأقل', error: true);
              return;
            }
            Navigator.pop(context, {
              'ref_type': 'custom',
              'name_ar': name,
              'calories': cal,
              'protein': double.tryParse(_protein.text) ?? 0,
              'carbs': double.tryParse(_carbs.text) ?? 0,
              'fat': double.tryParse(_fat.text) ?? 0,
            });
          },
          child: const Text('أضف'),
        ),
      ],
    );
  }

  Widget _numField(TextEditingController c, String label) => TextField(
        controller: c,
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        decoration: InputDecoration(labelText: label),
      );
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

  Future<void> _editRecipe(Map recipe) async {
    await Navigator.push(context, MaterialPageRoute(builder: (_) => RecipeBuilderScreen(recipe: recipe)));
    _load();
  }

  Future<void> _deleteRecipe(Map recipe) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('حذف الوصفة؟'),
        content: Text('هتشيل وصفة «${recipe['name_ar']}» نهائياً.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('إلغاء')),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.danger),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('احذف'),
          ),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    try {
      await Api.deleteRecipe(recipe['id']);
      if (!mounted) return;
      showSnack(context, 'اتحذفت الوصفة 👍');
      _load();
    } catch (e) {
      if (mounted) showSnack(context, ApiClient.errorMessage(e), error: true);
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
                    return Dismissible(
                      key: ValueKey(r['id']),
                      direction: DismissDirection.endToStart,
                      confirmDismiss: (_) async {
                        await _deleteRecipe(r);
                        return false;
                      },
                      background: Container(
                        alignment: Alignment.centerLeft,
                        padding: const EdgeInsets.only(left: 24),
                        decoration: BoxDecoration(color: AppColors.danger, borderRadius: BorderRadius.circular(12)),
                        child: const Icon(Icons.delete, color: Colors.white),
                      ),
                      child: Card(
                        child: ListTile(
                          leading: const Icon(Icons.soup_kitchen, color: AppColors.teal),
                          title: Text(r['name_ar']),
                          subtitle: Text('${r['servings']} أنفار • نصيب الفرد ${r['per_serving_calories']} سعرة'),
                          trailing: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              IconButton(
                                icon: Icon(Icons.edit_outlined, color: mutedColor(context)),
                                tooltip: 'تعديل',
                                onPressed: () => _editRecipe(r),
                              ),
                              const Icon(Icons.add_circle, color: AppColors.teal),
                            ],
                          ),
                          onTap: () => _logPortion(r),
                          onLongPress: () => _deleteRecipe(r),
                        ),
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

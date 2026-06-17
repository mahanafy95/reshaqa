import 'package:flutter/material.dart';

import '../core/api_client.dart';
import '../core/theme.dart';
import '../services/api.dart';

const _meals = {'breakfast': 'فطار', 'lunch': 'غدا', 'dinner': 'عشا', 'snack': 'سناك'};

class _Msg {
  _Msg(this.role, this.text);
  final String role; // user | bot
  final String text;
}

/// تبويب المساعد الذكي — اكتب أكلك بالعامية ويفهمه ويسجّله (مجاني بالكامل).
class MealChatTab extends StatefulWidget {
  const MealChatTab({super.key, required this.meal, required this.date, this.onLogged});
  final String meal;
  final String date;
  final VoidCallback? onLogged;

  @override
  State<MealChatTab> createState() => _MealChatTabState();
}

class _MealChatTabState extends State<MealChatTab> {
  final _input = TextEditingController();
  final _scroll = ScrollController();
  final List<_Msg> _msgs = [
    _Msg('bot',
        'اكتبلي أكلت إيه بالعامية، مثلاً: «النهاردة فطرت بيضتين وكوباية لبن ورغيف، وعلى الغدا طبق رز وفرخة». أنا أفهمه وأحسب السعرات وأسجّلهولك.'),
  ];
  List<Map<String, dynamic>> _pending = [];
  bool _busy = false;

  void _scrollDown() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(_scroll.position.maxScrollExtent,
            duration: const Duration(milliseconds: 250), curve: Curves.easeOut);
      }
    });
  }

  Future<void> _send() async {
    final text = _input.text.trim();
    if (text.isEmpty || _busy) return;
    setState(() {
      _msgs.add(_Msg('user', text));
      _input.clear();
      _busy = true;
    });
    _scrollDown();
    try {
      final r = await Api.parseMeal(text, date: widget.date, defaultMeal: widget.meal);
      final items = (r['items'] as List? ?? []).map((e) => Map<String, dynamic>.from(e)).toList();
      setState(() {
        _msgs.add(_Msg('bot', (r['reply_ar'] as String?) ?? 'فهمت.'));
        _pending = items;
      });
    } catch (e) {
      setState(() => _msgs.add(_Msg('bot', ApiClient.errorMessage(e))));
    } finally {
      setState(() => _busy = false);
      _scrollDown();
    }
  }

  double get _pendingTotal =>
      _pending.fold(0.0, (s, x) => s + ((x['calories'] as num?)?.toDouble() ?? 0));

  Future<void> _logAll() async {
    if (_pending.isEmpty || _busy) return;
    setState(() => _busy = true);
    try {
      for (final it in _pending) {
        await Api.addFood({
          'date': widget.date,
          'meal': it['meal'],
          'name_ar': it['name_ar'],
          'amount': (it['grams'] as num?)?.toDouble() ?? 1,
          'calories': (it['calories'] as num?)?.toDouble() ?? 0,
          'protein': (it['protein'] as num?)?.toDouble() ?? 0,
          'carbs': (it['carbs'] as num?)?.toDouble() ?? 0,
          'fat': (it['fat'] as num?)?.toDouble() ?? 0,
          'source': 'manual',
        });
      }
      final n = _pending.length;
      final tot = _pendingTotal.round();
      setState(() {
        _msgs.add(_Msg('bot', 'تمام ✅ سجّلت $n صنف بمجموع $tot سعرة.'));
        _pending = [];
      });
      widget.onLogged?.call();
    } catch (e) {
      setState(() => _msgs.add(_Msg('bot', ApiClient.errorMessage(e))));
    } finally {
      setState(() => _busy = false);
      _scrollDown();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Expanded(
          child: ListView.builder(
            controller: _scroll,
            padding: const EdgeInsets.all(12),
            itemCount: _msgs.length + (_pending.isNotEmpty ? 1 : 0),
            itemBuilder: (_, i) {
              if (i < _msgs.length) return _bubble(_msgs[i]);
              return _pendingCard();
            },
          ),
        ),
        SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(8, 0, 8, 8),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _input,
                    textInputAction: TextInputAction.send,
                    onSubmitted: (_) => _send(),
                    decoration: const InputDecoration(hintText: 'اكتب أكلت إيه…', isDense: true),
                  ),
                ),
                const SizedBox(width: 6),
                ElevatedButton(
                  onPressed: _busy ? null : _send,
                  child: _busy
                      ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                      : const Text('ابعت'),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _bubble(_Msg m) {
    final isUser = m.role == 'user';
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 3),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.82),
        decoration: BoxDecoration(
          color: isUser ? AppColors.teal : const Color(0xFFEDEDED),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Text(m.text, style: TextStyle(color: isUser ? Colors.white : AppColors.textDark)),
      ),
    );
  }

  Widget _pendingCard() {
    return Card(
      margin: const EdgeInsets.only(top: 8),
      child: Padding(
        padding: const EdgeInsets.all(10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('راجع/عدّل قبل التسجيل:', style: TextStyle(color: AppColors.textMuted, fontSize: 12)),
            const SizedBox(height: 4),
            ..._pending.asMap().entries.map((e) => _pendingRow(e.key, e.value)),
            const Divider(),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('المجموع ≈ ${_pendingTotal.round()} سعرة',
                    style: const TextStyle(fontWeight: FontWeight.bold, color: AppColors.teal)),
                ElevatedButton(onPressed: _busy ? null : _logAll, child: const Text('سجّل الكل')),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _pendingRow(int i, Map<String, dynamic> it) {
    final conf = it['confidence'] as String? ?? 'medium';
    final confColor = conf == 'high'
        ? AppColors.teal
        : conf == 'low'
            ? AppColors.textMuted
            : AppColors.orange;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          Container(width: 8, height: 8, decoration: BoxDecoration(color: confColor, shape: BoxShape.circle)),
          const SizedBox(width: 6),
          Expanded(child: Text('${it['name_ar']}', overflow: TextOverflow.ellipsis)),
          DropdownButton<String>(
            value: it['meal'] as String?,
            underline: const SizedBox(),
            isDense: true,
            items: _meals.entries.map((m) => DropdownMenuItem(value: m.key, child: Text(m.value, style: const TextStyle(fontSize: 12)))).toList(),
            onChanged: (v) => setState(() => it['meal'] = v),
          ),
          Text('${(it['calories'] as num?)?.round() ?? 0}', style: const TextStyle(fontWeight: FontWeight.bold)),
          const Text(' سعرة', style: TextStyle(fontSize: 11, color: AppColors.textMuted)),
          TextButton(
            style: TextButton.styleFrom(minimumSize: const Size(32, 32), padding: EdgeInsets.zero),
            onPressed: () => setState(() => _pending.removeAt(i)),
            child: const Text('✕', style: TextStyle(color: AppColors.danger, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }
}

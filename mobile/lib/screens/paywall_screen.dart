import 'package:flutter/material.dart';
import 'package:in_app_purchase/in_app_purchase.dart';
import 'package:provider/provider.dart';

import '../core/theme.dart';
import '../services/billing_service.dart';
import '../state/app_state.dart';
import '../widgets/common.dart';

/// شاشة الاشتراك (Premium) — تعرض الخطط من Google Play وتبدأ الشراء.
class PaywallScreen extends StatefulWidget {
  const PaywallScreen({super.key});
  @override
  State<PaywallScreen> createState() => _PaywallScreenState();
}

class _PaywallScreenState extends State<PaywallScreen> {
  bool _loading = true;
  bool _buying = false;

  static const _features = [
    ('📊', 'التقارير الأسبوعية والشهرية التفصيلية + تصدير PDF للطبيب'),
    ('🍲', 'وصفات بلا حدود + مسح الباركود + مكتبة أطعمة أوسع'),
    ('⌚', 'مزامنة الصحة (هواوي / Health Connect) + خطط أهداف متقدمة'),
    ('💚', 'دعم استمرار التطبيق وتطويره'),
  ];

  @override
  void initState() {
    super.initState();
    BillingService.onEntitlementChanged = () {
      if (mounted) context.read<AppState>().refreshPremium();
    };
    BillingService.onPurchaseResult = (success, error) {
      if (!mounted) return;
      setState(() => _buying = false);
      if (success) {
        showSnack(context, 'تم تفعيل اشتراكك 🎉 استمتع بكل المميزات');
        Navigator.of(context).maybePop();
      } else if (error != null) {
        showSnack(context, error, error: true);
      }
    };
    _init();
  }

  Future<void> _init() async {
    await BillingService.init();
    if (mounted) setState(() => _loading = false);
  }

  @override
  void dispose() {
    BillingService.onPurchaseResult = null;
    super.dispose();
  }

  Future<void> _buy(ProductDetails p) async {
    setState(() => _buying = true);
    try {
      await BillingService.buy(p);
    } catch (e) {
      if (mounted) {
        setState(() => _buying = false);
        showSnack(context, 'تعذّر بدء الشراء. حاول تاني.', error: true);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final products = BillingService.products;
    return Scaffold(
      appBar: AppBar(title: const Text('رشاقة Premium 💎')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(20),
              children: [
                const SizedBox(height: 4),
                const Center(child: Text('✨', style: TextStyle(fontSize: 48))),
                const SizedBox(height: 8),
                const Center(
                  child: Text('افتح كل مميزات رشاقة',
                      style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                ),
                const SizedBox(height: 20),
                ..._features.map((f) => Padding(
                      padding: const EdgeInsets.symmetric(vertical: 6),
                      child: Row(children: [
                        Text(f.$1, style: const TextStyle(fontSize: 22)),
                        const SizedBox(width: 12),
                        Expanded(child: Text(f.$2, style: const TextStyle(fontSize: 15))),
                      ]),
                    )),
                const SizedBox(height: 20),
                if (!BillingService.available || products.isEmpty)
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: AppColors.orange.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Text(
                      'الاشتراكات مش متاحة على الجهاز ده حالياً. تأكد إن التطبيق متثبّت من Google Play وإنك مسجّل دخول بحساب جوجل.',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: AppColors.textDark),
                    ),
                  )
                else
                  ...products.map((p) => Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: _PlanCard(product: p, busy: _buying, onTap: () => _buy(p)),
                      )),
                const SizedBox(height: 8),
                TextButton(
                  onPressed: _buying
                      ? null
                      : () async {
                          final app = context.read<AppState>();
                          await BillingService.restore();
                          app.refreshPremium();
                          if (mounted) showSnack(context, 'بنستعيد مشترياتك…');
                        },
                  child: const Text('استعادة المشتريات'),
                ),
                const SizedBox(height: 8),
                const Text(
                  'التجديد تلقائي، وتقدر تلغيه في أي وقت من Google Play. التجربة المجانية '
                  'تتحوّل لاشتراك مدفوع لو ملغتهاش قبل ما تخلص. الأسعار بتشمل الضرائب حسب بلدك.',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: AppColors.textMuted, fontSize: 12),
                ),
              ],
            ),
    );
  }
}

class _PlanCard extends StatelessWidget {
  const _PlanCard({required this.product, required this.busy, required this.onTap});
  final ProductDetails product;
  final bool busy;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: busy ? null : onTap,
      borderRadius: BorderRadius.circular(14),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          border: Border.all(color: AppColors.teal, width: 1.5),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(product.title.replaceAll(RegExp(r'\(.*\)'), '').trim(),
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  if (product.description.isNotEmpty)
                    Text(product.description,
                        style: const TextStyle(color: AppColors.textMuted, fontSize: 13)),
                ],
              ),
            ),
            const SizedBox(width: 12),
            busy
                ? const SizedBox(
                    height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                : Text(product.price,
                    style: const TextStyle(
                        fontWeight: FontWeight.bold, fontSize: 16, color: AppColors.teal)),
          ],
        ),
      ),
    );
  }
}

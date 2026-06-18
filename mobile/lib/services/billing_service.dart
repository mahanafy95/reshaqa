import 'dart:async';

import 'package:in_app_purchase/in_app_purchase.dart';

import 'api.dart';

/// معرّف منتج الاشتراك في Google Play (نفس GOOGLE_PLAY_PRODUCT_IDS بالباك-إند).
const String kPremiumProductId = 'reshaqa_premium';

/// غلاف لمشتريات Google Play — الشراء، الاستعادة، والتحقّق عبر الخادم.
///
/// مبدأ أمان: التفعيل لا يتم على العميل أبداً — نبعت رمز الشراء للخادم اللي
/// بيتحقّق منه عند Google ويفعّل الاشتراك، وبعدها نحدّث حالة الواجهة.
class BillingService {
  static final InAppPurchase _iap = InAppPurchase.instance;
  static StreamSubscription<List<PurchaseDetails>>? _sub;
  static List<ProductDetails> products = [];
  static bool available = false;

  /// يُستدعى بعد نجاح تحقّق الخادم من شراء — لتحديث حالة Premium في الواجهة.
  static void Function()? onEntitlementChanged;

  /// يُستدعى عند انتهاء محاولة شراء (نجاح/فشل/إلغاء) لإيقاف مؤشّر التحميل.
  static void Function(bool success, String? error)? onPurchaseResult;

  static Future<void> init() async {
    available = await _iap.isAvailable();
    if (!available) return;
    _sub ??= _iap.purchaseStream.listen(_onPurchases, onError: (_) {});
    await loadProducts();
  }

  static Future<void> loadProducts() async {
    try {
      final resp = await _iap.queryProductDetails({kPremiumProductId});
      products = resp.productDetails;
    } catch (_) {
      products = [];
    }
  }

  static Future<void> buy(ProductDetails product) async {
    await _iap.buyNonConsumable(purchaseParam: PurchaseParam(productDetails: product));
  }

  static Future<void> restore() async {
    await _iap.restorePurchases();
  }

  static Future<void> _onPurchases(List<PurchaseDetails> purchases) async {
    for (final p in purchases) {
      if (p.status == PurchaseStatus.error) {
        onPurchaseResult?.call(false, p.error?.message);
      } else if (p.status == PurchaseStatus.canceled) {
        onPurchaseResult?.call(false, null);
      } else if (p.status == PurchaseStatus.purchased || p.status == PurchaseStatus.restored) {
        final token = p.verificationData.serverVerificationData;
        try {
          await Api.verifyPurchase(p.productID, token);
          onEntitlementChanged?.call();
          onPurchaseResult?.call(true, null);
        } catch (_) {
          // الخادم هيتأكد لاحقاً عبر RTDN — منعرضش خطأ مزعج
          onEntitlementChanged?.call();
        }
      }
      if (p.pendingCompletePurchase) {
        await _iap.completePurchase(p);
      }
    }
  }

  static void dispose() {
    _sub?.cancel();
    _sub = null;
  }
}

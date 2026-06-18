/// وحدات القياس والسكر — للموبايل (نفس منطق الويب). التحويل للجرام (كثافة السوائل ~1).
class UnitDef {
  final String key;
  final String label;
  final double grams;
  const UnitDef(this.key, this.label, this.grams);
}

const foodUnits = <UnitDef>[
  UnitDef('g', 'جرام', 1),
  UnitDef('ml', 'مل', 1),
  UnitDef('tsp', 'معلقة صغيرة', 5),
  UnitDef('tbsp', 'معلقة كبيرة', 15),
  UnitDef('cup', 'كوب (~240مل)', 240),
];

UnitDef unitByKey(String k) => foodUnits.firstWhere((u) => u.key == k, orElse: () => foodUnits.first);
double toGrams(double qty, String unitKey) => qty * unitByKey(unitKey).grams;
String unitText(double qty, String unitKey) {
  final q = qty == qty.roundToDouble() ? qty.round().toString() : qty.toString();
  return unitKey == 'g' ? '$q جم' : '$q ${unitByKey(unitKey).label}';
}

class SugarDef {
  final String key;
  final String label;
  final double calPerG;
  final double carbPerG;
  const SugarDef(this.key, this.label, this.calPerG, this.carbPerG);
}

const sugarTypes = <SugarDef>[
  SugarDef('none', 'بدون سكر', 0, 0),
  SugarDef('white', 'سكر أبيض', 4, 1),
  SugarDef('brown', 'سكر بني', 3.9, 0.98),
  SugarDef('stevia', 'استيفيا (صفر سعرات)', 0, 0),
];
SugarDef sugarByKey(String k) => sugarTypes.firstWhere((s) => s.key == k, orElse: () => sugarTypes.first);

const sugarUnits = <UnitDef>[
  UnitDef('tsp', 'معلقة صغيرة (~4جم)', 4),
  UnitDef('tbsp', 'معلقة كبيرة (~12جم)', 12),
  UnitDef('g', 'جرام', 1),
];
UnitDef sugarUnitByKey(String k) => sugarUnits.firstWhere((u) => u.key == k, orElse: () => sugarUnits.first);

"""不锈钢网带物料插件"""
class StainlessSteelMaterial:
    material_type = "不锈钢"
    grades = ["304", "316", "310S"]
    density_table = {"304": 7930, "316": 8000, "310S": 7980}

    def get_density(self, grade="304"):
        return self.density_table.get(grade, 7930)

    def validate(self, grade):
        return grade in self.grades

from plugins import PluginRegistry
PluginRegistry.register("material", "stainless_steel", StainlessSteelMaterial)

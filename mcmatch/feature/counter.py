'''
Mnemonic Counter features

@author: niko
'''
from mcmatch.db.types import FnFeature, Fn, Codeblock
from mcmatch.x86 import expensive_mnemonics, jump_mnemonics, arith_mnemonics, bitop_mnemonics, call_mnemonics

class MultiMnemonicCounterFeature(FnFeature):
  """Instruction Mnemonic Counter. Does not take operand types into account.
  A comparison of instructions by execution time/latency can be found
  in http://www.agner.org/optimize/instruction_tables.pdf
  """
  group = None
  default_mnemonics = expensive_mnemonics

  def __init__(self, mnemonics=None, group=None, relative=False):
    self.table = {}
    if mnemonics is not None:
      self.mnemonics = mnemonics
    else:
      self.mnemonics = self.default_mnemonics
    
    self.relative = relative
    if group is None:
      group = "expensive"
    self.group = group

  def num_features(self):
    return len(self.mnemonics)
  
  def _get_mnemonics(self):
    if self.mnemonics is not None:
      return self.mnemonics
    else:
      return self.default_mnemonics
  
  def get_kv(self):
    return self.table

  def calculate_from_histogram(self, histogram):
    mnemonics = self._get_mnemonics()
    self.table = {}
    all_sum = sum(histogram.values()) * 1.0
    for mnemonic in mnemonics:
      if mnemonic in histogram:
        self.table[mnemonic] = histogram[mnemonic]
        if self.relative:
          self.table[mnemonic] /= all_sum
      else:
        self.table[mnemonic] = 0

  def calculate(self, fn):
    assert isinstance(fn, Codeblock)
    self.table = []
    self.calculate_from_histogram(fn.get_mnemonic_histogram())

  def get_sql_columns(self, fq_select=True, fq_rename=False):
    suffix = ""
    if self.relative:
      suffix = "_rel"
      
    columns = ["mn_%s%s" % (x, suffix) for x in self._get_mnemonics()]
    return self._sql_prep_cols(columns, self.get_sql_table(), fq_select, fq_rename)
  
  def get_sql_contents(self):
    mnemonics = self._get_mnemonics()
    if len(self.table):
      return [self.table[x] for x in mnemonics]
    return [None]*len(mnemonics)

  def get_sql_table(self):
    tblname = "feature_mncounter_" + self.group
    if self.relative:
      return tblname + "_relative"
    return tblname
  
  def create_table_ddl(self):
    dt = "integer"
    suffix = ''
    if self.relative:
      dt = "float"
      suffix = '_rel'
    
    return "  " + ",\n  ".join(['mn_%s%s %s' % (x, suffix, dt) for x in self._get_mnemonics()])


# class RelativeMultiMnemonicCounterFeature(MultiMnemonicCounterFeature):
#   def create_table_ddl(self):
#     return "  " + ",\n  ".join(['mn_r_%s float' % x for x in self._get_mnemonics()])
#   
#   def get_sql_columns(self, fq_select=True, fq_rename=False):
#     columns = ["mn_r_%s" % x for x in self._get_mnemonics()]
#     return self._sql_prep_cols(columns, self.get_sql_table(), fq_select, fq_rename)
#   
#   def get_sql_table(self):
#     return "mnemonic_counter_relative_feature"
#   
#   def calculate_from_histogram(self, histogram):
#     s = sum(histogram.values())      
#     MultiMnemonicCounterFeature.calculate_from_histogram(self, histogram)
#     for k in self.table.keys():
#       self.table[k] = (1.0 * self.table[k]) / s


class ArithCounter(MultiMnemonicCounterFeature):
  def __init__(self, relative=False):
    super(ArithCounter, self).__init__(arith_mnemonics, group="arith", relative=relative)

#class RelativeArithCounter(RelativeMultiMnemonicCounterFeature):
#  def __init__(self):
#    super(RelativeArithCounter, self).__init__(arith_mnemonics, group="arith")
#
#  def get_sql_table(self):
#    return "arith_counter_relative_feature"


class BitOpCounter(MultiMnemonicCounterFeature):
  def __init__(self, relative=False):
    super(BitOpCounter, self).__init__(
      bitop_mnemonics, group="bitop", relative=relative)




class JmpCounter(MultiMnemonicCounterFeature):
  def __init__(self, relative=False):
    #TODO fix features
    super(JmpCounter, self).__init__(
       jump_mnemonics, group="jmp", relative=relative)

class CallCounter(MultiMnemonicCounterFeature):
  def __init__(self, relative=False):
    super(CallCounter, self).__init__(call_mnemonics, group="call", relative=relative)

class CounterSum(FnFeature):
  def __init__(self, underlying, relative=False):
    self.underlying = underlying(relative=relative)
    self.relative = relative
    assert isinstance(self.underlying, MultiMnemonicCounterFeature)

    self.field_name = "sum_" + self.underlying.group
  
  def calculate(self, fn):
    self.underlying.calculate(fn)
    kv = self.underlying.get_kv()
    s = 0
    for v in kv.values():
      s += v
    self.sum = s
  
  def create_table_ddl(self):
    dt = "INTEGER"
    if self.relative:
      dt = "FLOAT"
    return " %s %s " % (self.field_name, dt)
  
  def get_sql_table(self):
    return "sum_" + self.underlying.get_sql_table()
  
  def get_kv(self):
    return { self.field_name : self.sum }
  
  def get_sql_columns(self, fq_select=True, fq_rename=False):
    return self._sql_prep_cols([self.field_name], self.get_sql_table(), fq_select, fq_rename)
  
  def get_sql_contents(self):
    return [ self.sum ]
    
class CallCounterSum(CounterSum):
  def __init__(self, relative=False):
    super(CallCounterSum, self).__init__(CallCounter, relative=relative)
  
class JmpCounterSum(CounterSum):
  def __init__(self, relative=False):  
    super(JmpCounterSum, self).__init__(JmpCounter, relative=relative)

class ExpensiveCounterSum(CounterSum):
  def __init__(self, relative=False):
    super(ExpensiveCounterSum, self).__init__(MultiMnemonicCounterFeature, relative=relative)

class ArithCounterSum(CounterSum):
  def __init__(self, relative=False):
    super(ArithCounterSum, self).__init__(ArithCounter, relative=relative)

class BitOpCounterSum(CounterSum):
  def __init__(self, relative=False):
    super(BitOpCounterSum, self).__init__(BitOpCounter, relative=relative)

counter_features = {
  'expensive': MultiMnemonicCounterFeature(),
  'arithmetic': ArithCounter(),
  'logical': BitOpCounter(),
  'jumps': JmpCounter(),
  'calls': CallCounter()
}

#TODO: remove Sum() classes, replace with sum=True parameter
# on construction instead.
counter_sum_features = {
  'expensive_sum' : ExpensiveCounterSum(),
  'arithmetic_sum' : ArithCounterSum(),
  'logical_sum' : BitOpCounterSum(),
  'jumps_sum' : JmpCounterSum(),
  'call_sum' : CallCounterSum(),
}

relative_counter_features = {
  'r_expensive' : MultiMnemonicCounterFeature(relative=True),             
  'r_arith' : ArithCounter(relative=True),
  'r_logical': BitOpCounter(relative=True),
  'r_jumps' : JmpCounter(relative=True),
  'r_calls' : CallCounter(relative=True)
}

relative_counter_sum_features = {
  'r_expensive_sum' : ExpensiveCounterSum(relative=True),
  'r_arith_sum' : ArithCounterSum(relative=True),
  'r_logical_sum' : BitOpCounterSum(relative=True),
  'r_jumps_sum' : JmpCounterSum(relative=True),
  'r_call_sum' : CallCounterSum(relative=True)
}

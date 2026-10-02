library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
entity d5 is port (a : in std_ulogic; q : out std_ulogic); end entity;
architecture x of d5 is
  function f (i : std_ulogic) return std_ulogic is
    signal s_fn : std_ulogic;
  begin
    return i;
  end function f;
begin
  q <= f(a);
end architecture;

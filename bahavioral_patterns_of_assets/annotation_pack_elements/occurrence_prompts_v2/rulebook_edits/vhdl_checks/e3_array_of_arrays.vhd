library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
entity e3 is port (clk : in std_ulogic; i, j : in std_ulogic_vector(1 downto 0); q : out std_ulogic); end entity;
architecture x of e3 is
  type row_t is array (0 to 3) of std_ulogic_vector(3 downto 0);
  type mat_t is array (0 to 3) of row_t;
  signal m : mat_t;
begin
  p: process (clk) begin
    if rising_edge(clk) then
      q <= m(to_integer(unsigned(i)))(to_integer(unsigned(j)))(0);
    end if;
  end process p;
end architecture;

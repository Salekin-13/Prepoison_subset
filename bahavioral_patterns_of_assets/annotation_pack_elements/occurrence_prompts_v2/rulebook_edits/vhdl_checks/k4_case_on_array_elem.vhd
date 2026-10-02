library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
entity k4 is port (clk : in std_ulogic; idx : in std_ulogic_vector(1 downto 0); q : out std_ulogic); end entity;
architecture x of k4 is
  type mem_t is array (0 to 3) of std_ulogic_vector(1 downto 0);
  signal mem : mem_t;
begin
  p: process (clk) begin
    if rising_edge(clk) then
      case mem(to_integer(unsigned(idx))) is
        when "00" => q <= '0';
        when others => q <= '1';
      end case;
    end if;
  end process p;
end architecture;
